from PIL import Image, ImageDraw

# Crear imagen de prueba (sala simple)
img = Image.new('RGB', (512, 512), color=(240, 240, 240))
draw = ImageDraw.Draw(img)

# Piso
draw.rectangle([0, 350, 512, 512], fill=(180, 150, 120))

# Pared
draw.rectangle([0, 0, 512, 350], fill=(230, 230, 230))

# Sofá (rectángulo gris)
draw.rectangle([100, 250, 300, 350], fill=(120, 120, 120))
draw.rectangle([100, 200, 300, 250], fill=(100, 100, 100))

# Mesa (marrón)
draw.rectangle([320, 280, 420, 320], fill=(139, 90, 60))
draw.rectangle([340, 320, 400, 350], fill=(120, 80, 50))

# Guardar
img.save('renders_input/test_room.png')
print("✅ Imagen de prueba creada: renders_input/test_room.png")
