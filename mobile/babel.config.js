module.exports = function (api) {
  api.cache(true);
  
  // Safe require for react-native-worklets/plugin (may not exist)
  const workletsPlugin = [
    'react-native-reanimated/plugin',
    // Try to add worklets plugin, ignore if not found
    ...(function() {
      try { return [require.resolve('react-native-worklets/core')]; }
      catch { return []; }
    })(),
  ];

  return {
    presets: [
      ['babel-preset-expo', { jsxImportSource: 'nativewind' }],
      'nativewind/babel',
    ],
    plugins: workletsPlugin,
  };
};
