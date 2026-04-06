const fs = require('fs');
const path = require('path');
const dir = path.join(__dirname, '..', 'node_modules', 'react-native-worklets');
if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
const content = "module.exports = require('react-native-worklets-core/plugin');";
fs.writeFileSync(path.join(dir, 'plugin.js'), content, 'utf8');
console.log('Fixed!');
