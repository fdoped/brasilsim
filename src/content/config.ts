import { defineCollection, z } from 'astro:content';

const blog = defineCollection({
  type: 'content',
  schema: z.object({
    titulo: z.string(),
    descricao: z.string(),
    data: z.date(),
    autor: z.string().default('Bolaverso'),
    tags: z.array(z.string()).default([]),
  }),
});

export const collections = { blog };
