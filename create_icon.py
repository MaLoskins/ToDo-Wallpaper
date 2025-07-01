def create_app_icon(size=64):
    """Create application icon at specified size with adaptive design"""
    from PIL import Image, ImageDraw
    
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    s = size / 64.0
    
    if size >= 48:
        for i in range(int(30 * s)):
            a = int(255 * (1 - i/(30*s)))
            draw.ellipse([i, i, size-i, size-i], outline=(0, 122 if i < 15*s else 100, 204 if i < 15*s else 180, a if i < 15*s else a//2), width=1)
        draw.ellipse([8*s, 8*s, size-8*s, size-8*s], fill=(25, 30, 40))
        draw.ellipse([10*s, 10*s, size-10*s, size-10*s], fill=(35, 40, 55))
        for r, c in [(6, (15, 20, 30)), (5, (45, 50, 70)), (4, (55, 60, 85))]:
            draw.rounded_rectangle([20*s-r*s+2*s, 20*s-r*s+2*s, 44*s+r*s-2*s, 44*s+r*s-2*s], radius=int(r*s), fill=c)
        draw.rounded_rectangle([18*s, 18*s, 46*s, 46*s], radius=int(6*s), outline=(80, 180, 255), width=max(1, int(2*s)))
        draw.ellipse([22*s, 22*s, 32*s, 32*s], fill=(255, 255, 255, 30))
    else:
        draw.ellipse([2, 2, size-2, size-2], fill=(35, 40, 55))
        box = [size*0.25, size*0.25, size*0.75, size*0.75]
        draw.rounded_rectangle(box, radius=max(1, int(2*s)), fill=(55, 60, 85), outline=(100, 200, 255), width=1)
    
    check = [(23*s, 32*s), (28*s, 37*s), (41*s, 24*s)]
    if size >= 32:
        for o in [(1*s, 1*s)]:
            sp = [(p[0]+o[0], p[1]+o[1]) for p in check]
            draw.line(sp[0:2] + sp[1:3], fill=(0, 0, 0, 80), width=max(1, int(3*s)))
    draw.line(check[0:2] + check[1:3], fill=(100, 255, 150), width=max(1, int(3*s)))
    
    return img


if __name__ == "__main__":
    print("Utility script used in todo_app.py and todo_editor_module.py to create the application icon.")