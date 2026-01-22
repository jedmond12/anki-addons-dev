#!/usr/bin/env python3
"""
Shadow Mewtwo Sprite Cleanup Script
Removes white outlines and replaces with dark outlines while preserving animation.
"""

from PIL import Image, ImageEnhance, ImageFilter
import os

def replace_white_outline_with_dark(image):
    """
    Replace white/light outline pixels with dark charcoal/black outlines.
    Preserves the core colors of the sprite (purple, orange, etc.)
    """
    # Convert to RGBA if not already
    if image.mode != 'RGBA':
        image = image.convert('RGBA')

    pixels = image.load()
    width, height = image.size

    # Create a new image for the result
    result = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    result_pixels = result.load()

    for y in range(height):
        for x in range(width):
            r, g, b, a = pixels[x, y]

            # Skip fully transparent pixels
            if a == 0:
                result_pixels[x, y] = (0, 0, 0, 0)
                continue

            # Detect white/light gray outline pixels (high brightness, low saturation)
            # These are the pixels we want to replace with dark outlines
            brightness = (r + g + b) / 3

            # Check if this is a white/light outline pixel
            # White outlines typically have high R, G, B values and are similar
            color_variance = max(abs(r-g), abs(g-b), abs(r-b))

            # If it's a light color (brightness > 200) and relatively uniform (outline-like)
            if brightness > 200 and color_variance < 50:
                # Replace with dark charcoal/black outline
                result_pixels[x, y] = (20, 20, 25, a)  # Very dark charcoal
            # If it's a medium-light gray outline (brightness 150-200)
            elif brightness > 150 and color_variance < 60:
                # Replace with dark outline
                result_pixels[x, y] = (25, 25, 30, a)  # Dark charcoal
            # Otherwise, keep the original pixel (body colors, shading, etc.)
            else:
                result_pixels[x, y] = (r, g, b, a)

    return result

def sharpen_and_enhance(image):
    """
    Slightly sharpen the image and enhance definition.
    """
    # Apply subtle sharpening
    sharpened = image.filter(ImageFilter.SHARPEN)

    # Blend original with sharpened (70% sharpened, 30% original for subtlety)
    result = Image.blend(image, sharpened, 0.4)

    # Slightly enhance contrast for better definition
    enhancer = ImageEnhance.Contrast(result)
    result = enhancer.enhance(1.15)

    return result

def process_animated_gif(input_path, output_path):
    """
    Process an animated GIF, cleaning up outlines while preserving animation.
    """
    print(f"Processing: {input_path}")

    # Open the GIF
    img = Image.open(input_path)

    # Get animation properties
    frames = []
    durations = []

    try:
        frame_count = 0
        while True:
            # Get frame duration
            duration = img.info.get('duration', 100)
            durations.append(duration)

            # Process the frame
            frame = img.convert('RGBA')

            # Step 1: Replace white outlines with dark outlines
            frame = replace_white_outline_with_dark(frame)

            # Step 2: Sharpen and enhance
            frame = sharpen_and_enhance(frame)

            frames.append(frame)
            frame_count += 1

            # Move to next frame
            img.seek(img.tell() + 1)
    except EOFError:
        pass  # End of frames

    print(f"  Processed {len(frames)} frames")

    # Save as animated GIF with same timing
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,  # Loop forever
        transparency=0,
        disposal=2,  # Clear frame before rendering next
        optimize=False  # Don't optimize to preserve quality
    )

    print(f"  Saved to: {output_path}")

def main():
    """Process both Shadow Mewtwo sprites."""

    # Define paths
    base_dir = "/home/user/anki-addons-dev/1908235722/user_files/sprites"

    sprites = [
        {
            'input': f"{base_dir}/front_default_gif/150_shadow_front.gif",
            'output': f"{base_dir}/front_default_gif/150_shadow_front.gif"
        },
        {
            'input': f"{base_dir}/back_default_gif/150_shadow_back.gif",
            'output': f"{base_dir}/back_default_gif/150_shadow_back.gif"
        }
    ]

    # Also update the shadow_mewtwo_project copies
    project_sprites = [
        {
            'input': f"{base_dir}/shadow_mewtwo_project/150_shadow_front.gif",
            'output': f"{base_dir}/shadow_mewtwo_project/150_shadow_front.gif"
        },
        {
            'input': f"{base_dir}/shadow_mewtwo_project/150_shadow_back.gif",
            'output': f"{base_dir}/shadow_mewtwo_project/150_shadow_back.gif"
        }
    ]

    print("Shadow Mewtwo Sprite Cleanup")
    print("=" * 50)

    # Process main sprites
    for sprite in sprites:
        if os.path.exists(sprite['input']):
            process_animated_gif(sprite['input'], sprite['output'])
        else:
            print(f"Warning: {sprite['input']} not found")

    # Process project copies
    print("\nUpdating project copies...")
    for sprite in project_sprites:
        if os.path.exists(sprite['input']):
            process_animated_gif(sprite['input'], sprite['output'])
        else:
            print(f"Warning: {sprite['input']} not found")

    print("\n" + "=" * 50)
    print("Cleanup complete!")

if __name__ == "__main__":
    main()
