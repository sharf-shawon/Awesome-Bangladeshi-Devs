import { readFileSync, existsSync } from "fs";
import { join, dirname } from "path";
import { fileURLToPath } from "url";

const __dirname = dirname(fileURLToPath(import.meta.url));

export default function() {
  let url = process.env.SITE_URL || "";
  
  if (!url) {
    const cnamePath = join(__dirname, "../../CNAME");
    if (existsSync(cnamePath)) {
      const cname = readFileSync(cnamePath, "utf8").trim();
      if (cname) {
        url = `https://${cname}`;
      }
    }
  }
  
  // Fallback for local development if CNAME is missing
  if (!url) {
    url = "http://localhost:8080";
  }

  // Ensure no trailing slash
  url = url.replace(/\/$/, "");

  return {
    url: url
  };
}
