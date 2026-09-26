import math
import uuid

def parse_owocr_file(owocr_data, img_filename):
    
    img_width = owocr_data['image_properties']['width']
    img_height = owocr_data['image_properties']['height']

    mokuro_page = {
        "version": "0.2.4",
        "img_width": img_width,
        "img_height": img_height,
        "img_path": img_filename,
        "blocks": []
    }

    for para in owocr_data.get('paragraphs', []):
        writing_dir = para.get('writing_direction', 'LEFT_TO_RIGHT')
        vertical = writing_dir == 'TOP_TO_BOTTOM'

        lines_text = []
        lines_coords = []
        font_sizes = []

        all_x = []
        all_y = []

        for line in para.get('lines', []):
            lines_text.append(line['text'])

            bbox = line['bounding_box']
            
            cx = bbox['center_x'] * img_width
            cy = bbox['center_y'] * img_height
            w = bbox['width'] * img_width
            h = bbox['height'] * img_height
            rot = bbox.get('rotation_z') or 0.0

            if vertical:
                font_sizes.append(w)
            else:
                font_sizes.append(h)

            cos_a = math.cos(rot)
            sin_a = math.sin(rot)

            corners_relative = [
                (-w / 2, -h / 2),
                (w / 2, -h / 2),
                (w / 2, h / 2),
                (-w / 2, h / 2)
            ]

            line_poly = []
            for dx, dy in corners_relative:
                rx = dx * cos_a - dy * sin_a
                ry = dx * sin_a + dy * cos_a
                x = cx + rx
                y = cy + ry
                
                line_poly.append([round(x, 1), round(y, 1)])
                all_x.append(x)
                all_y.append(y)

            lines_coords.append(line_poly)

        if not lines_coords:
            continue

        font_size = int(round(sum(font_sizes) / len(font_sizes))) if font_sizes else 16
        
        box = [
            int(math.floor(min(all_x))),
            int(math.floor(min(all_y))),
            int(math.ceil(max(all_x))),
            int(math.ceil(max(all_y)))
        ]

        mokuro_page['blocks'].append({
            "box": box,
            "vertical": vertical,
            "font_size": font_size,
            "lines_coords": lines_coords,
            "lines": lines_text
        })

    return mokuro_page

def generate_mokuro_volume(title, title_uuid, volume_name, volume_json_data):
    
    volume_data = {
        "version": "0.2.4",
        "title": title,
        "title_uuid": title_uuid,
        "volume": volume_name,
        "volume_uuid": str(uuid.uuid4()),
        "pages": []
    }

    for json_data in volume_json_data:
        page_data = parse_owocr_file(json_data['json_data'], json_data['filename'])
        volume_data["pages"].append(page_data)

    return volume_data

