import { z } from "zod";

const uuidSchema = z.string().uuid();
const decimalSchema = z.union([z.string(), z.number()]).nullable();

export const healthSchema = z.object({
  status: z.literal("ok"),
  service: z.string().min(1),
});

export const categoryAttributeSchema = z.object({
  key: z.string(),
  label: z.string(),
  value_type: z.string(),
  is_required: z.boolean(),
  options: z.array(z.string()).nullable(),
});

export const categorySchema = z.object({
  id: uuidSchema,
  slug: z.string(),
  name: z.string(),
  attributes: z.array(categoryAttributeSchema),
});

export const categoriesSchema = z.array(categorySchema);

export const publicListingSchema = z.object({
  id: uuidSchema,
  category_id: uuidSchema,
  title: z.string(),
  description: z.string(),
  price: decimalSchema,
  city: z.string(),
  attributes: z.record(z.string(), z.unknown()),
  ai_generated_fields: z.array(z.string()),
  cover_image_url: z.string().nullable(),
  seller_id: uuidSchema.nullable(),
  seller_name: z.string().nullable(),
  seller_trust_badge: z.string().nullable(),
  created_at: z.iso.datetime({ offset: true }),
});

export const searchResponseSchema = z.object({
  items: z.array(publicListingSchema),
  total: z.number().int().nonnegative(),
  limit: z.number().int().positive(),
  offset: z.number().int().nonnegative(),
});

export type Health = z.infer<typeof healthSchema>;
export type Category = z.infer<typeof categorySchema>;
export type PublicListing = z.infer<typeof publicListingSchema>;
export type SearchResponse = z.infer<typeof searchResponseSchema>;
