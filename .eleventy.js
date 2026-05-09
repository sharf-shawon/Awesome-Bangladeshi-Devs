const { DateTime } = require("luxon");

module.exports = function(eleventyConfig) {
  // Pass-through files
  eleventyConfig.addPassthroughCopy("data/*.json");
  eleventyConfig.addPassthroughCopy("assets");

  // Filters
  eleventyConfig.addFilter("readableDate", (dateObj) => {
    return DateTime.fromISO(dateObj, { zone: "utc" }).toLocaleString(DateTime.DATE_FULL);
  });

  eleventyConfig.addFilter("limit", function(array, limit) {
    return array.slice(0, limit);
  });

  return {
    dir: {
      input: "site",
      output: "_site",
      includes: "_includes"
    },
    templateFormats: ["md", "njk", "html"],
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk"
  };
};
