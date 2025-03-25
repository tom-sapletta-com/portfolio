This implementation:

Extracts the thumbnail generation functionality from the original code
Provides a clean API for use as a library
Adds command-line interface with various options
Maintains the same thumbnail generation strategies:
Open Graph image
Twitter Card image
Largest image on the page
Placeholder with domain color
You can use it in two ways:

As a command-line tool:
```
python screenshot.py https://example.com -o example.jpg -w 400 -h 300 -q 90
```

As a library in your code:
```        
from screenshot import capture_thumbnail

# Save to file
capture_thumbnail("https://example.com", "thumbnails/example.jpg")

# Or get PIL Image object
image = capture_thumbnail("https://example.com")
# Do something with the image...
```