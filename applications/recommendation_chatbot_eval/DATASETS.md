# Recommendation Catalog Dataset Inventory

This document records the source datasets currently in scope for the
recommendation chatbot application. The common interface is a normalized
candidate catalog: a list of recommendable items with text, metadata, and
optional signals.

## Normalized Item Contract

Required fields:

- `item_id`: stable item identifier within the normalized catalog.
- `domain`: broad recommendation domain, such as `movie`, `ecommerce`,
  `local_business`, or `fashion`.
- `title`: human-readable item name.
- `display_text`: text shown to or used by the recommendation bot. This is
  generated from title, description, and metadata when the source lacks a clean
  description field.
- `source`: source dataset metadata.

Recommended fields:

- `description`: source description, plot, product detail, or business summary
  when available.
- `categories`: normalized tags or high-level categories.
- `metadata`: cross-domain metadata such as price, location, brand, language,
  release year, image URLs, or feature text.

Optional fields:

- `signals`: ranking or popularity signals, such as rating, review count,
  popularity, sales rank, vote count, or revenue.
- `constraints`: structured properties useful for hard filtering.
- `domain_metadata`: domain-specific source fields that should not be forced
  into the shared schema.

## Dataset Summary

| Source | Domain | Item list | Useful item fields | Signals | Access plan | v0 status |
|---|---|---:|---|---|---|---|
| Amazon Reviews 2023 | `ecommerce` | Yes | `parent_asin`, title, description, features, category, price, images | average rating, rating number, reviews | Hugging Face / McAuley loader by category config, especially `raw_meta_<category>` | Later, streaming/category subset |
| WebShop | `ecommerce` | Yes | product title, description, price, category path, images, attributes/options | task reward and product metadata; not a clean rating source | Official WebShop setup, using small mode first | Later |
| Yelp Open Dataset | `local_business` | Yes | business id, name, categories, attributes, hours, location | stars, review count, check-ins/reviews | Official JSON archive; read `business.json` first, avoid loading all reviews | Later |
| Google Local Data 2021 | `local_business` | Yes | name, address, geo, description, category, price, hours, misc info | ratings and review text | Use smaller subsets, state-level metadata, or k-core/CSV files before full data | Later |
| H&M Personalized Fashion | `fashion` | Yes | `article_id`, product name, product type/group, color, department, garment group, detail description | transactions; no simple rating | Kaggle download; read `articles.csv` first, skip images for v0 | Later |
| CMU Movie Summary Corpus | `movie` | Yes | movie id, name, plot summary, genres, release date, runtime, languages, countries, revenue, character/actor metadata | box office revenue only; no user rating | Direct 46 MB download; local cache is acceptable | First local test |

## Source Notes

### Amazon Reviews 2023

Use only item metadata for the first catalog adapter. The full dataset is too
large for default local development. The adapter should accept a category config
and a limit, for example `raw_meta_All_Beauty` with `limit=1000`.

Expected mapping:

- `item_id`: `parent_asin`
- `title`: source title
- `description`: joined source description list, if present
- `categories`: main category and category path, if present
- `metadata`: features, price, images
- `signals`: average rating, rating number

### WebShop

WebShop is already an environment-like shopping benchmark with real products.
For this application, use it only as a product catalog source at first. The
adapter should consume the product records produced by the official setup, not
reimplement the WebShop environment.

Expected mapping:

- `item_id`: source product identifier or ASIN-like id
- `title`: product name
- `description`: product description
- `categories`: category path
- `metadata`: price, images, attributes/options

### Yelp Open Dataset

Use businesses as recommendable items. For v0, avoid full review ingestion. The
business file has enough metadata to recommend restaurants and local services.
Reviews can later be summarized into `display_text` or aggregated into signals.

Expected mapping:

- `item_id`: `business_id`
- `title`: business name
- `description`: generated from categories, attributes, and hours
- `categories`: Yelp categories
- `metadata`: address, city/state, latitude/longitude, attributes, hours
- `signals`: stars, review count

### Google Local Data 2021

The full dataset is much larger than needed for local testing. Use state-level
metadata or smaller k-core/CSV subsets. Treat businesses as recommendable items.

Expected mapping:

- `item_id`: source business id
- `title`: business name
- `description`: source description when available
- `categories`: category information
- `metadata`: address, geo, price, open hours, misc info
- `signals`: rating and review aggregates when available

### H&M Personalized Fashion

Use `articles.csv` as the first catalog source. Image files and transaction
history are optional for later recommendation baselines, not required for the
catalog interface.

Expected mapping:

- `item_id`: `article_id`
- `title`: product name
- `description`: detail description
- `categories`: product group/type, department, garment group
- `metadata`: color, graphical appearance, index/group names
- `signals`: derived from transactions later, not required in v0

### CMU Movie Summary Corpus

Use this as the first local testing source because it is small enough for local
development and has clean plot summaries plus aligned metadata.

Expected mapping:

- `item_id`: `cmu:<wikipedia_movie_id>`
- `title`: movie name
- `description`: plot summary
- `categories`: genres
- `metadata`: release date, runtime, languages, countries
- `signals`: box office revenue if present
- `domain_metadata`: Freebase id and character/actor fields if joined later

## Data Storage Policy

Commit:

- schema files,
- source documentation,
- adapter code,
- reproducible download/normalization instructions.

Do not commit:

- full raw archives,
- full normalized catalogs,
- image folders,
- review dumps,
- Kaggle/Hugging Face cache directories.

Use local gitignored paths:

```text
data/raw/<source_name>/
data/normalized/recommendation_catalogs/<source_name>/items.jsonl
data/normalized/recommendation_catalogs/<source_name>/items.parquet
```
