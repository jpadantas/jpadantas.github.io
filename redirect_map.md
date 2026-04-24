# URL Mapping for Indexing Fix

The following table maps the 404 URLs reported by Google Search Console to their current locations in the repository.

| Old URL (404) | New Current URL | Notes |
| :--- | :--- | :--- |
| `files/dantas2012study_slides.pdf` | `files/dantas2012estudo_slides.pdf` | Renamed English -> Portuguese |
| `files/dantas2022asa.pdf` | `files/dantas2025asa.pdf` | Updated version |
| `files/aprovado_no_ita.pdf` | `certificates/2010_ITA_Entrance_Exam.pdf` | Moved and renamed |
| `files/figueiredo2025analise.pdf` | `files/araujo2025analise.pdf` | Renamed (based on authors) |
| `files/wsc_diversity_award_2024.pdf` | `certificates/2024_WSC_Diversity_Award.pdf` | Moved to certificates |
| `files/iymc.pdf` | `certificates/2019_IYMC_Ambassador.pdf` | Moved and renamed |
| `files/asa-registro.pdf` | `certificates/2024_ASA_Software_Registry.pdf` | Moved and renamed |

## Recommendations for the User

1. **GitHub Upload**: Push the updated `sitemap.xml` and `404.html` to your GitHub repository.
2. **Search Console**:
   - Go to **Sitemaps** and resubmit `sitemap.xml`.
   - Go to **Indexing > Pages** and clicking on the 404 errors, then click **"Validate Fix"**.
   - For critical files, use the **URL Inspection** tool on the NEW URLs and click **"Request Indexing"**.
   - For the **"Bloqueada pelo robots.txt"** errors on existing PDFs (e.g. `dantas2012estudo_slides.pdf`), use the URL Inspection tool to verify they are now accessible, then click **"Validate Fix"**.
   - For the **"Cópia sem canônica"** error on `patrikar2025image.pdf`, use the URL Inspection tool to request re-indexing.
3. **External Links**: If possible, update any external profiles (LinkedIn, ResearchGate, etc.) that might still be linking to the old filenames.

