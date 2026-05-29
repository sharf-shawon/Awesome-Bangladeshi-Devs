export default async function() {
  const { default: getEnriched } = await import("./enriched.js");
  const enriched = getEnriched();
  
  const langMap = {};
  for (const dev of enriched) {
    const langs = dev.all_languages || [];
    for (const lang of langs) {
      if (!lang) continue;
      if (!langMap[lang]) {
        langMap[lang] = {
          name: lang,
          slug: lang.toLowerCase()
            .replace(/\+/g, "p")
            .replace(/#/g, "sharp")
            .replace(/[^a-z0-9]+/g, "-")
            .replace(/^-+|-+$/g, ""),
          count: 0,
          devs: []
        };
      }
      langMap[lang].count += 1;
      langMap[lang].devs.push(dev);
    }
  }
  
  return Object.values(langMap).sort((a, b) => b.count - a.count);
}
