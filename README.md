# Bond Shipping and Trading Website

Static corporate website for Bond Shipping and Trading Limited.

## Structure

- `dist/` contains the complete deployable website.
- `dist/assets/css/` contains shared styles.
- `dist/assets/js/` contains shared interactions.
- `dist/assets/images/` contains optimized WebP images.
- `dist/assets/video/` contains the optimized hero video.
- `server/` contains the enquiry API that records submissions to CSV.

## Local preview

For page-only preview, open `dist/index.html` directly. To preview the enquiry submission flow, run:

```powershell
python server/inquiry_server.py
```

Then visit `http://127.0.0.1:8011/`. Submissions are saved to `data/inquiries.csv` by default.

## Deployment

Deploy the contents of `dist/` to the web root. Run `server/inquiry_server.py` as a private service and reverse proxy `/api/inquiries` to `127.0.0.1:8011`. Set `BOND_INQUIRY_DIR` to a private writable directory outside the web root.
