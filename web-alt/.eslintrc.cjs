/** @type {import('eslint').Linter.Config} */
module.exports = {
  root: true,
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint"],
  extends: [
    "next/core-web-vitals",
    "prettier",
  ],
  rules: {
    "@typescript-eslint/no-explicit-any": "off",
  },
};
