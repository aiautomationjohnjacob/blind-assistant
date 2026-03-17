module.exports = function (api) {
  api.cache(true);
  return {
    presets: ["babel-preset-expo"],
    plugins: [
      // Module resolver for @/* path aliases (matches tsconfig.json paths)
      [
        "module-resolver",
        {
          root: ["."],
          alias: {
            "@": "./src",
            "@services": "./src/services",
            "@screens": "./src/screens",
            "@components": "./src/components",
            "@hooks": "./src/hooks",
          },
        },
      ],
    ],
  };
};
