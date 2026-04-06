const fs = require('fs');
const path = require('path');

// Fix: react-native-css-interop references wrong module path
// It looks for 'react-native-worklets/plugin' but the actual package is 'react-native-worklets-core'
const workletsDir = path.join(__dirname, '..', 'node_modules', 'react-native-worklets');
const pluginFile = path.join(workletsDir, 'plugin.js');

try {
  if (!fs.existsSync(workletsDir)) {
    fs.mkdirSync(workletsDir, { recursive: true });
  }
  fs.writeFileSync(pluginFile, "module.exports = require('react-native-worklets-core/plugin');");
  console.log('[postinstall] Fixed react-native-worklets/plugin redirect');
} catch (e) {
  console.error('[postinstall] Failed to fix:', e.message);
}
