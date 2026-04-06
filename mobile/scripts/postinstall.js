const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

// Fix react-native-worklets module alias for react-native-reanimated compatibility
const workletsDir = path.join(__dirname, '..', 'node_modules', 'react-native-worklets');

try {
  if (!fs.existsSync(workletsDir)) {
    fs.mkdirSync(workletsDir, { recursive: true });
  }
  
  // plugin.js for babel
  fs.writeFileSync(path.join(workletsDir, 'plugin.js'), 
    "module.exports = require('react-native-worklets-core/plugin');");
  
  // index.js for direct imports  
  fs.writeFileSync(path.join(workletsDir, 'index.js'),
    "module.exports = require('react-native-worklets-core');");
    
  // package.json so node recognizes it as a module
  fs.writeFileSync(path.join(workletsDir, 'package.json'), JSON.stringify({
    name: 'react-native-worklets',
    version: '1.0.0',
    main: 'index.js'
  }));
    
  console.log('[postinstall] ✓ Fixed react-native-worklets module');
} catch (e) {
  console.error('[postinstall] Error:', e.message);
}
