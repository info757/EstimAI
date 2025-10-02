# Template Images

Place template images here for template matching detection:

- `water.png` - Water utility symbols
- `sewer.png` - Sewer utility symbols  
- `storm.png` - Storm drain symbols

## Template Requirements

- PNG format
- Grayscale images work best
- Small, focused symbols (not full page images)
- High contrast for better matching
- Recommended size: 50x50 to 200x200 pixels

## Usage

The detection system will automatically load these templates if they exist.
If no templates are found, the system falls back to synthetic detections for demo purposes.
