import { mkdir, copyFile, readdir, stat } from "node:fs/promises";
import { join } from "node:path";

async function copyRecursive(srcDir, dstDir) {
  await mkdir(dstDir, { recursive: true });
  const entries = await readdir(srcDir, { withFileTypes: true });
  for (const entry of entries) {
    const srcPath = join(srcDir, entry.name);
    const dstPath = join(dstDir, entry.name);
    if (entry.isDirectory()) {
      await copyRecursive(srcPath, dstPath);
      continue;
    }
    if (entry.isFile()) {
      await copyFile(srcPath, dstPath);
    }
  }
}

async function main() {
  // Minimal build step: copy static files into dist/
  await mkdir("dist", { recursive: true });

  // Copy top-level static files
  for (const name of ["index.html"]) {
    await copyFile(name, join("dist", name));
  }

  // Copy optional assets dir if present
  try {
    const s = await stat("assets");
    if (s.isDirectory()) {
      await copyRecursive("assets", join("dist", "assets"));
    }
  } catch {
    // no assets/
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});

