import { defineCollection, z } from "astro:content";
import { glob } from "astro/loaders";

const guide = defineCollection({
  loader: glob({ pattern: "**/*.md", base: "./src/content/guide" }),
  schema: z.object({
    title: z.string(),
    description: z.string(),
    excerpt: z.string(),
    date: z.string(),
    author: z.string().default("Kenny"),
    readMin: z.number(),
    category: z.enum(["toilet", "dev"]),
    label: z.string(),
  }),
});

export const collections = { guide };
