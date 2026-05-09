const fs = require("fs");
const path = require("path");

module.exports = function() {
  const filePath = path.resolve(__dirname, "../../data/users-enriched.json");
  if (fs.existsSync(filePath)) {
    const rawData = fs.readFileSync(filePath, "utf-8");
    return JSON.parse(rawData);
  }
  return [];
};
