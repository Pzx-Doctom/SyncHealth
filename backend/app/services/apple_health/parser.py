
"""
Apple HealthKit export XML stream parser
Supports both legacy format (<HealthData>/<Record>) and CDA format (<ClinicalDocument>/<observation>)
"""
import xml.etree.ElementTree as ET
from typing import Iterator, Dict, Any, Callable, Optional
from datetime import datetime, timedelta
import logging
import re

from app.services.apple_health.converter import (
    ACTIVITY_TYPE_MAP, HEART_RATE_TYPE_MAP, SLEEP_STAGE_MAP,
    WORKOUT_TYPE_MAP, ECG_CLASSIFICATION_MAP,
    convert_unit, parse_iso_datetime, parse_duration_seconds,
    generate_uuid, get_sleep_stage, get_workout_type,
    get_heart_rate_measurement_type, infer_motion_context,
)

logger = logging.getLogger(__name__)

NS = "{urn:hl7-org:v3}"
XSI_TYPE = "{http://www.w3.org/2001/XMLSchema-instance}type"


def detect_format(xml_path: str) -> str:
    """
    Detect XML format by reading the root element.
    Returns "cda" or "legacy"
    """
    for event, elem in ET.iterparse(xml_path, events=("start",)):
        if elem.tag == f"{NS}ClinicalDocument":
            return "cda"
        elif elem.tag == "HealthData":
            return "legacy"
        break
    return "unknown"


def parse_cda_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse CDA datetime format: "20250717093819+0800"
    Also handles "20250717093819.000+0800" and similar variants
    """
    if not dt_str:
        return None
    dt_str = dt_str.strip()

    # Pattern: YYYYMMDDHHMMSS+TZ or YYYYMMDDHHMMSS.SSS+TZ
    patterns = [
        (r"(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})[.]?(\d*)([+-]\d{4})", "%Y%m%d%H%M%S"),
    ]

    for regex, _ in patterns:
        m = re.match(regex, dt_str)
        if m:
            try:
                year, month, day, hour, minute, second = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5)), int(m.group(6))
                tz_str = m.group(8)
                # Parse timezone offset
                tz_sign = 1 if tz_str[0] == "+" else -1
                tz_hours = int(tz_str[1:3])
                tz_minutes = int(tz_str[3:5])
                from datetime import timezone, timedelta as td
                tz_offset = td(hours=tz_sign * tz_hours, minutes=tz_sign * tz_minutes)
                tz = timezone(tz_offset)

                frac = m.group(7)
                microsecond = 0
                if frac:
                    # Pad or truncate to 6 digits for microseconds
                    frac = frac[:6].ljust(6, "0")
                    microsecond = int(frac)

                return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tz)
            except (ValueError, IndexError):
                continue

    # Fallback to standard parser
    return parse_iso_datetime(dt_str)


class CDAHealthXMLParser:
    """
    Parser for Apple HealthKit CDA (Clinical Document Architecture) format export.
    This is the format used by iOS 16+ when exporting health data.
    """

    def __init__(self, xml_path: str, progress_callback: Optional[Callable[[int, int], None]] = None):
        self.xml_path = xml_path
        self.progress_callback = progress_callback
        self.stats = {
            "total_records": 0,
            "heart_rates": 0,
            "hrv_samples": 0,
            "activity_samples": 0,
            "sleep_sessions": 0,
            "sleep_stages": 0,
            "blood_oxygen": 0,
            "body_temperature": 0,
            "respiratory_rate": 0,
            "ecg_records": 0,
            "workout_records": 0,
            "noise_exposure": 0,
            "mindfulness_sessions": 0,
            "skipped": 0,
            "errors": 0,
        }

    def parse(self) -> Iterator[Dict[str, Any]]:
        """
        Stream-parse the CDA XML file, yielding parsed records one at a time.
        """
        context = ET.iterparse(self.xml_path, events=("start", "end"))
        context = iter(context)

        try:
            event, root = next(context)
        except StopIteration:
            logger.error("XML file is empty or malformed")
            return
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return

        # Collect children of the current observation
        current_children = {}
        current_attribs = {}

        for event, elem in context:
            if event == "start":
                if elem.tag == f"{NS}observation":
                    current_attribs = dict(elem.attrib)
                    current_children = {}
                continue

            if event == "end":
                tag = elem.tag

                # Collect children of observation
                if current_attribs:
                    tag_local = tag.replace(NS, "")
                    attribs = dict(elem.attrib)
                    text_val = (elem.text or "").strip()
                    current_children[tag_local] = {
                        "attribs": attribs,
                        "text": text_val if text_val else None,
                    }

                # End of observation - process it
                if tag == f"{NS}observation" and current_attribs:
                    record = self._parse_observation(current_attribs, current_children)
                    if record:
                        self.stats["total_records"] += 1
                        self.stats[record["_counter_key"]] = self.stats.get(record["_counter_key"], 0) + 1
                        yield record
                    else:
                        self.stats["skipped"] += 1
                    current_attribs = {}
                    current_children = {}

                elem.clear()

        root.clear()

    def _parse_observation(self, attribs: dict, children: dict) -> Optional[Dict[str, Any]]:
        """Parse a single CDA observation element"""
        # Get the HK type from the <type> child element
        type_elem = children.get("type", {})
        hk_type = type_elem.get("text", "")

        if not hk_type:
            return None

        # Get value
        value_elem = children.get("value", {})
        value_attrs = value_elem.get("attribs", {})
        raw_value = value_attrs.get("value", "")
        unit = value_attrs.get("unit", "")

        # Get time range
        low_elem = children.get("low", {})
        high_elem = children.get("high", {})
        start_str = low_elem.get("attribs", {}).get("value", "")
        end_str = high_elem.get("attribs", {}).get("value", "")

        # Get source
        source_elem = children.get("sourceName", {})
        source_name = source_elem.get("text", "")

        # Get device info
        device_elem = children.get("device", {})
        device_text = device_elem.get("text", "")

        # Get metadata
        metadata = {}
        key_elem = children.get("key", {})
        meta_elem = children.get("metadataEntry", {})
        if key_elem.get("text"):
            metadata[key_elem["text"]] = meta_elem.get("text", "")

        # Generate UUID
        sample_uuid = generate_uuid(hk_type, start_str, raw_value, source_name)

        # Route to the appropriate parser
        if hk_type in ACTIVITY_TYPE_MAP:
            return self._build_activity(hk_type, raw_value, unit, start_str, end_str, source_name, sample_uuid)
        elif hk_type in HEART_RATE_TYPE_MAP:
            return self._build_heart_rate(hk_type, raw_value, unit, start_str, end_str, source_name, sample_uuid, metadata)
        elif hk_type == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":
            return self._build_hrv(raw_value, unit, start_str, source_name, sample_uuid)
        elif hk_type == "HKQuantityTypeIdentifierOxygenSaturation":
            return self._build_blood_oxygen(raw_value, unit, start_str, source_name, sample_uuid)
        elif hk_type == "HKQuantityTypeIdentifierBodyTemperature":
            return self._build_body_temperature(raw_value, unit, start_str, source_name, sample_uuid)
        elif hk_type == "HKQuantityTypeIdentifierRespiratoryRate":
            return self._build_respiratory_rate(raw_value, start_str, source_name, sample_uuid)
        elif hk_type == "HKQuantityTypeIdentifierEnvironmentalAudioExposure":
            return self._build_noise_exposure(raw_value, unit, start_str, end_str, source_name, sample_uuid)
        elif hk_type == "HKCategoryTypeIdentifierSleepAnalysis":
            return self._build_sleep(raw_value, start_str, end_str, source_name, sample_uuid)
        elif hk_type == "HKCategoryTypeIdentifierMindfulSession":
            return self._build_mindfulness(start_str, end_str, source_name, sample_uuid)
        else:
            logger.debug(f"Unhandled HK type: {hk_type}")
            return None

    def _parse_value(self, raw_value: str) -> float:
        """Parse numeric value, return 0 on failure"""
        try:
            return float(raw_value)
        except (ValueError, TypeError):
            return 0.0

    def _build_activity(self, hk_type, raw_value, unit, start_str, end_str, source, uuid):
        metric_type = ACTIVITY_TYPE_MAP.get(hk_type, "unknown")
        value = self._parse_value(raw_value)
        converted = value
        if metric_type == "distance_meters" and unit == "km":
            converted = convert_unit(value, "km", "m")
        elif metric_type in ("active_energy_kcal", "resting_energy_kcal") and unit == "kJ":
            converted = convert_unit(value, "kJ", "kcal")
        duration = None
        start_dt = parse_cda_datetime(start_str)
        end_dt = parse_cda_datetime(end_str)
        if start_dt and end_dt:
            duration = (end_dt - start_dt).total_seconds()
        return {
            "type": "activity",
            "_counter_key": "activity_samples",
            "sample_uuid": uuid,
            "metric_type": metric_type,
            "value": converted,
            "duration_seconds": duration,
            "recorded_at": start_dt,
            "source_device": source,
        }

    def _build_heart_rate(self, hk_type, raw_value, unit, start_str, end_str, source, uuid, metadata):
        bpm = self._parse_value(raw_value)
        motion_context = infer_motion_context(metadata)
        measurement_type = get_heart_rate_measurement_type(hk_type)
        return {
            "type": "heart_rate",
            "_counter_key": "heart_rates",
            "sample_uuid": uuid,
            "bpm": bpm,
            "motion_context": motion_context,
            "measurement_type": measurement_type,
            "recorded_at": parse_cda_datetime(start_str),
            "source_device": source,
        }

    def _build_hrv(self, raw_value, unit, start_str, source, uuid):
        sdnn = self._parse_value(raw_value)
        if unit == "s":
            sdnn = sdnn * 1000
        return {
            "type": "hrv",
            "_counter_key": "hrv_samples",
            "sample_uuid": uuid,
            "sdnn_ms": sdnn,
            "recorded_at": parse_cda_datetime(start_str),
            "source_device": source,
        }

    def _build_blood_oxygen(self, raw_value, unit, start_str, source, uuid):
        value = self._parse_value(raw_value)
        spo2 = value * 100 if unit in ("", "fraction") else value
        return {
            "type": "blood_oxygen",
            "_counter_key": "blood_oxygen",
            "sample_uuid": uuid,
            "spo2_percent": spo2,
            "measurement_condition": None,
            "recorded_at": parse_cda_datetime(start_str),
            "source_device": source,
        }

    def _build_body_temperature(self, raw_value, unit, start_str, source, uuid):
        temp = self._parse_value(raw_value)
        if unit == "degF":
            temp = convert_unit(temp, "degF", "degC")
        return {
            "type": "body_temperature",
            "_counter_key": "body_temperature",
            "sample_uuid": uuid,
            "temperature_celsius": temp,
            "measurement_location": None,
            "recorded_at": parse_cda_datetime(start_str),
            "source_device": source,
        }

    def _build_respiratory_rate(self, raw_value, start_str, source, uuid):
        rate = self._parse_value(raw_value)
        return {
            "type": "respiratory_rate",
            "_counter_key": "respiratory_rate",
            "sample_uuid": uuid,
            "breaths_per_minute": rate,
            "recorded_at": parse_cda_datetime(start_str),
            "source_device": source,
        }

    def _build_noise_exposure(self, raw_value, unit, start_str, end_str, source, uuid):
        decibels = self._parse_value(raw_value)
        start_dt = parse_cda_datetime(start_str)
        end_dt = parse_cda_datetime(end_str)
        duration = None
        if start_dt and end_dt:
            duration = (end_dt - start_dt).total_seconds()
        return {
            "type": "noise_exposure",
            "_counter_key": "noise_exposure",
            "sample_uuid": uuid,
            "decibels": decibels,
            "duration_seconds": duration,
            "recorded_at": start_dt,
            "source_device": source,
        }

    def _build_sleep(self, raw_value, start_str, end_str, source, uuid):
        # CDA sleep uses the value text for sleep stage
        # The value element might have text like HKCategoryValueSleepAnalysisAsleepDeep
        # Or the raw_value might be a category code
        stage = get_sleep_stage(raw_value)
        if not stage:
            # Try common CDA sleep values
            sleep_map = {
                "HKCategoryValueSleepAnalysisInBed": "in_bed",
                "HKCategoryValueSleepAnalysisAsleep": "asleep",
                "HKCategoryValueSleepAnalysisAwake": "awake",
                "HKCategoryValueSleepAnalysisAsleepCore": "core",
                "HKCategoryValueSleepAnalysisAsleepDeep": "deep",
                "HKCategoryValueSleepAnalysisAsleepREM": "rem",
                "0": "in_bed",
                "1": "asleep",
                "2": "awake",
                "3": "core",
                "4": "deep",
                "5": "rem",
            }
            stage = sleep_map.get(raw_value)
        if not stage:
            return None
        start_dt = parse_cda_datetime(start_str)
        end_dt = parse_cda_datetime(end_str)
        if not start_dt or not end_dt:
            return None
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        return {
            "type": "sleep_stage",
            "_counter_key": "sleep_stages",
            "sample_uuid": uuid,
            "stage": stage,
            "start_time": start_dt,
            "end_time": end_dt,
            "duration_minutes": duration_minutes,
            "source_device": source,
            "is_in_bed": (stage == "in_bed"),
            "is_asleep": (stage in ("asleep", "core", "deep", "rem")),
        }

    def _build_mindfulness(self, start_str, end_str, source, uuid):
        start_dt = parse_cda_datetime(start_str)
        end_dt = parse_cda_datetime(end_str)
        if not start_dt or not end_dt:
            return None
        duration_minutes = (end_dt - start_dt).total_seconds() / 60
        return {
            "type": "mindfulness",
            "_counter_key": "mindfulness_sessions",
            "sample_uuid": uuid,
            "start_time": start_dt,
            "end_time": end_dt,
            "duration_minutes": duration_minutes,
            "source_device": source,
        }


class LegacyHealthXMLParser:
    """
    Parser for the legacy Apple HealthKit export format (<HealthData>/<Record>).
    Used for exports from older iOS versions.
    """

    def __init__(self, xml_path: str, progress_callback: Optional[Callable[[int, int], None]] = None):
        self.xml_path = xml_path
        self.progress_callback = progress_callback
        self.stats = {
            "total_records": 0,
            "heart_rates": 0,
            "hrv_samples": 0,
            "activity_samples": 0,
            "sleep_sessions": 0,
            "sleep_stages": 0,
            "blood_oxygen": 0,
            "body_temperature": 0,
            "respiratory_rate": 0,
            "ecg_records": 0,
            "workout_records": 0,
            "noise_exposure": 0,
            "mindfulness_sessions": 0,
            "skipped": 0,
            "errors": 0,
        }

    def parse(self) -> Iterator[Dict[str, Any]]:
        context = ET.iterparse(self.xml_path, events=("start", "end"))
        context = iter(context)
        try:
            event, root = next(context)
        except StopIteration:
            logger.error("XML file is empty or malformed")
            return
        except ET.ParseError as e:
            logger.error(f"XML parse error: {e}")
            return

        for event, elem in context:
            if event == "end":
                tag = elem.tag
                try:
                    if tag == "Record":
                        record = self._parse_record(elem)
                        if record:
                            self.stats["total_records"] += 1
                            self.stats[record["_counter_key"]] = self.stats.get(record["_counter_key"], 0) + 1
                            yield record
                        else:
                            self.stats["skipped"] += 1
                        # 只在 Record 处理完后 clear（含子树），避免子元素
                        # MetadataEntry/Statistics 被提前 clear 导致属性丢失
                        elem.clear()
                    elif tag == "Workout":
                        record = self._parse_workout(elem)
                        if record:
                            self.stats["total_records"] += 1
                            self.stats["workout_records"] += 1
                            yield record
                        else:
                            self.stats["skipped"] += 1
                        elem.clear()
                except Exception as e:
                    self.stats["errors"] += 1
                    logger.warning(f"Parse error: {e}")
                    elem.clear()

        root.clear()

    def _parse_record(self, elem) -> Optional[Dict[str, Any]]:
        attrs = dict(elem.attrib)
        record_type = attrs.get("type", "")
        if record_type in ACTIVITY_TYPE_MAP:
            return self._parse_activity_record(attrs, elem)
        elif record_type in HEART_RATE_TYPE_MAP:
            return self._parse_heart_rate_record(attrs, elem)
        elif record_type == "HKQuantityTypeIdentifierHeartRateVariabilitySDNN":
            return self._parse_hrv_record(attrs, elem)
        elif record_type == "HKQuantityTypeIdentifierOxygenSaturation":
            return self._parse_blood_oxygen_record(attrs, elem)
        elif record_type == "HKQuantityTypeIdentifierBodyTemperature":
            return self._parse_body_temperature_record(attrs, elem)
        elif record_type == "HKQuantityTypeIdentifierRespiratoryRate":
            return self._parse_respiratory_rate_record(attrs, elem)
        elif record_type == "HKQuantityTypeIdentifierEnvironmentalAudioExposure":
            return self._parse_noise_exposure_record(attrs, elem)
        elif record_type == "HKCategoryTypeIdentifierSleepAnalysis":
            return self._parse_sleep_record(attrs, elem)
        elif record_type == "HKCategoryTypeIdentifierElectrocardiogram":
            return self._parse_ecg_record(attrs, elem)
        elif record_type == "HKCategoryTypeIdentifierMindfulSession":
            return self._parse_mindfulness_record(attrs, elem)
        return None

    def _get_uuid(self, attrs: dict) -> str:
        uuid_val = attrs.get("HKObjectUUID", "")
        if uuid_val:
            return uuid_val
        return generate_uuid(
            record_type=attrs.get("type", ""),
            start_date=attrs.get("startDate", ""),
            value=attrs.get("value", ""),
            source=attrs.get("sourceName", ""),
        )

    def _parse_activity_record(self, attrs, elem):
        record_type = attrs.get("type", "")
        metric_type = ACTIVITY_TYPE_MAP.get(record_type, "unknown")
        value = float(attrs.get("value", 0))
        unit = attrs.get("unit", "")
        converted_value = value
        if metric_type == "distance_meters" and unit == "km":
            converted_value = convert_unit(value, "km", "m")
        elif metric_type in ("active_energy_kcal", "resting_energy_kcal") and unit == "kJ":
            converted_value = convert_unit(value, "kJ", "kcal")
        duration = parse_duration_seconds(attrs.get("startDate", ""), attrs.get("endDate", ""))
        return {
            "type": "activity", "_counter_key": "activity_samples",
            "sample_uuid": self._get_uuid(attrs), "metric_type": metric_type,
            "value": converted_value, "duration_seconds": duration,
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_heart_rate_record(self, attrs, elem):
        record_type = attrs.get("type", "")
        bpm = float(attrs.get("value", 0))
        metadata = self._extract_metadata(elem)
        return {
            "type": "heart_rate", "_counter_key": "heart_rates",
            "sample_uuid": self._get_uuid(attrs), "bpm": bpm,
            "motion_context": infer_motion_context(metadata),
            "measurement_type": get_heart_rate_measurement_type(record_type),
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_hrv_record(self, attrs, elem):
        sdnn = float(attrs.get("value", 0))
        unit = attrs.get("unit", "ms")
        if unit == "s":
            sdnn = sdnn * 1000
        return {
            "type": "hrv", "_counter_key": "hrv_samples",
            "sample_uuid": self._get_uuid(attrs), "sdnn_ms": sdnn,
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_sleep_record(self, attrs, elem):
        value = attrs.get("value", "")
        stage = get_sleep_stage(value)
        if not stage:
            return None
        start = parse_iso_datetime(attrs.get("startDate", ""))
        end = parse_iso_datetime(attrs.get("endDate", ""))
        if not start or not end:
            return None
        return {
            "type": "sleep_stage", "_counter_key": "sleep_stages",
            "sample_uuid": self._get_uuid(attrs), "stage": stage,
            "start_time": start, "end_time": end,
            "duration_minutes": (end - start).total_seconds() / 60,
            "source_device": attrs.get("sourceName", ""),
            "is_in_bed": (stage == "in_bed"),
            "is_asleep": (stage in ("asleep", "core", "deep", "rem")),
        }

    def _parse_blood_oxygen_record(self, attrs, elem):
        value = float(attrs.get("value", 0))
        unit = attrs.get("unit", "")
        spo2 = value * 100 if unit in ("", "fraction") else value
        return {
            "type": "blood_oxygen", "_counter_key": "blood_oxygen",
            "sample_uuid": self._get_uuid(attrs), "spo2_percent": spo2,
            "measurement_condition": None,
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_body_temperature_record(self, attrs, elem):
        temp = float(attrs.get("value", 0))
        unit = attrs.get("unit", "degC")
        if unit == "degF":
            temp = convert_unit(temp, "degF", "degC")
        return {
            "type": "body_temperature", "_counter_key": "body_temperature",
            "sample_uuid": self._get_uuid(attrs), "temperature_celsius": temp,
            "measurement_location": None,
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_respiratory_rate_record(self, attrs, elem):
        return {
            "type": "respiratory_rate", "_counter_key": "respiratory_rate",
            "sample_uuid": self._get_uuid(attrs),
            "breaths_per_minute": float(attrs.get("value", 0)),
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_ecg_record(self, attrs, elem):
        value = attrs.get("value", "")
        classification = ECG_CLASSIFICATION_MAP.get(value, "inconclusive")
        metadata = self._extract_metadata(elem)
        avg_hr = None
        for k, v in metadata.items():
            if "HeartRate" in k:
                try:
                    avg_hr = float(v)
                except (ValueError, TypeError):
                    pass
        return {
            "type": "ecg", "_counter_key": "ecg_records",
            "sample_uuid": self._get_uuid(attrs), "classification": classification,
            "average_heart_rate": avg_hr, "symptoms_status": None,
            "voltage_measurements": None,
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_noise_exposure_record(self, attrs, elem):
        return {
            "type": "noise_exposure", "_counter_key": "noise_exposure",
            "sample_uuid": self._get_uuid(attrs),
            "decibels": float(attrs.get("value", 0)),
            "duration_seconds": parse_duration_seconds(attrs.get("startDate", ""), attrs.get("endDate", "")),
            "recorded_at": parse_iso_datetime(attrs.get("startDate", "")),
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_mindfulness_record(self, attrs, elem):
        start = parse_iso_datetime(attrs.get("startDate", ""))
        end = parse_iso_datetime(attrs.get("endDate", ""))
        if not start or not end:
            return None
        return {
            "type": "mindfulness", "_counter_key": "mindfulness_sessions",
            "sample_uuid": self._get_uuid(attrs),
            "start_time": start, "end_time": end,
            "duration_minutes": (end - start).total_seconds() / 60,
            "source_device": attrs.get("sourceName", ""),
        }

    def _parse_workout(self, elem):
        attrs = dict(elem.attrib)
        activity_type = attrs.get("workoutActivityType", "")
        workout_type = get_workout_type(activity_type)
        if not workout_type:
            workout_type = activity_type.replace("HKWorkoutActivityType", "").lower()
        start = parse_iso_datetime(attrs.get("startDate", ""))
        end = parse_iso_datetime(attrs.get("endDate", ""))
        if not start or not end:
            return None
        duration = (end - start).total_seconds()
        stats = {}
        for child in elem:
            if child.tag == "Statistics":
                st = child.get("type", "")
                su = child.get("unit", "")
                ss = child.get("sum", "")
                if ss:
                    stats[st] = {"value": float(ss), "unit": su}
        distance = 0
        if "HKQuantityTypeIdentifierDistanceWalkingRunning" in stats:
            d = stats["HKQuantityTypeIdentifierDistanceWalkingRunning"]["value"]
            u = stats["HKQuantityTypeIdentifierDistanceWalkingRunning"]["unit"]
            distance = convert_unit(d, u, "m") if u == "km" else d * 1000 if u == "mi" else d
        active_energy = 0
        if "HKQuantityTypeIdentifierActiveEnergyBurned" in stats:
            e = stats["HKQuantityTypeIdentifierActiveEnergyBurned"]["value"]
            u = stats["HKQuantityTypeIdentifierActiveEnergyBurned"]["unit"]
            active_energy = convert_unit(e, "kJ", "kcal") if u == "kJ" else e
        return {
            "type": "workout", "_counter_key": "workout_records",
            "sample_uuid": self._get_uuid(attrs), "workout_type": workout_type,
            "start_time": start, "end_time": end, "duration_seconds": duration,
            "total_energy_kcal": active_energy, "active_energy_kcal": active_energy,
            "distance_meters": distance if distance else None,
            "avg_heart_rate": None, "max_heart_rate": None, "min_heart_rate": None,
            "source_device": attrs.get("sourceName", ""), "hr_zones": [],
        }

    def _extract_metadata(self, elem):
        metadata = {}
        for child in elem:
            if child.tag == "MetadataEntry":
                k = child.get("key", "")
                v = child.get("value", "")
                metadata[k] = v
        return metadata


def create_parser(xml_path: str, progress_callback=None):
    """
    Factory function: detect format and return appropriate parser instance.
    """
    fmt = detect_format(xml_path)
    if fmt == "cda":
        logger.info("Detected CDA format export")
        return CDAHealthXMLParser(xml_path, progress_callback)
    elif fmt == "legacy":
        logger.info("Detected legacy format export")
        return LegacyHealthXMLParser(xml_path, progress_callback)
    else:
        logger.warning("Unknown XML format, trying legacy parser")
        return LegacyHealthXMLParser(xml_path, progress_callback)


# Backward compatibility alias
HealthXMLParser = LegacyHealthXMLParser
