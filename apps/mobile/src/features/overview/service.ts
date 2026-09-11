import {
  categoriesSchema,
  healthSchema,
  searchResponseSchema,
  type Category,
  type PublicListing,
} from "@lava/api-contracts";

import type { ApiClient } from "../../api/client";

export type MarketplaceOverview = {
  service: string;
  categories: Category[];
  latestListings: PublicListing[];
  totalListings: number;
};

export async function loadMarketplaceOverview(
  client: ApiClient,
): Promise<MarketplaceOverview> {
  const [health, categories, search] = await Promise.all([
    client.get("/health", healthSchema),
    client.get("/categories", categoriesSchema),
    client.get("/search/listings?sort=newest&limit=5", searchResponseSchema),
  ]);
  return {
    service: health.service,
    categories,
    latestListings: search.items,
    totalListings: search.total,
  };
}
