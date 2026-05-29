import { DateTime } from "luxon";

export default function(eleventyConfig) {
  eleventyConfig.setUseGitIgnore(false);
  eleventyConfig.addPassthroughCopy("data/*.json");
  eleventyConfig.addPassthroughCopy("assets");
  eleventyConfig.addPassthroughCopy("site/robots.txt");
  eleventyConfig.addPassthroughCopy("CNAME");

  eleventyConfig.addFilter("readableDate", (d) => {
    if (!d) return "Unknown";
    const dt = DateTime.fromISO(d, { zone: "utc" });
    if (!dt.isValid) return "Unknown";
    return dt.toLocaleString(DateTime.DATE_FULL);
  });

  eleventyConfig.addFilter("slugifyLang", (str) => {
    if (!str) return "";
    return str.toLowerCase()
      .replace(/\+/g, "p").replace(/#/g, "sharp")
      .replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "");
  });

  eleventyConfig.addFilter("limit", (arr, n) => arr.slice(0, n));
  eleventyConfig.addFilter("sortBy", (arr, key) =>
    [...arr].sort((a, b) => (b[key] || 0) - (a[key] || 0))
  );
  eleventyConfig.addFilter("json", (val) => JSON.stringify(val));

  eleventyConfig.addFilter("localeString", (num) => {
    return (num || 0).toLocaleString();
  });

  return {
    dir: {
      input: "site",
      output: "_site",
      includes: "_includes",
      data: "_data"
    },
    templateFormats: ["md", "njk", "html"],
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk"
  };
}
