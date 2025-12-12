from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import os
from rembg import remove
import io
import random
import argparse
from gcs_utils import list_gcs_files, is_gcs_path

def generate_cover(
    bg_path,
    qimen_path,
    player_paths,  # List of player image paths
    title_lines,   # List of title text lines (e.g., ["火旺克金形势显", "刺锋遇曜力难前"])
    today_str,     # Date string in format "YYYY-MM-DD"
    output_filename="cover.jpg",
    output_dir="output/",
    image_size=(1024, 1536),  # 2:3 ratio, width 1024px height 1536px
    font_path=None,  # Optional path to calligraphy font file
    taiji_path=None,  # Optional path to taiji (Yin-Yang) image
    fog_path=None,  # Optional path to fog image
    circle_path=None,  # Optional path to circle image to overlay on cells
    circle_cells=None,  # Optional list of cell numbers (1-9) to overlay circle, where grid is: [[1,2,3],[4,5,6],[7,8,9]]
    footer_path=None  # Optional path to footer image to overlay at the bottom
):
    """
    生成奇门球探风格的封面图。

    参数:
    - bg_path: 背景图片路径
    - qimen_path: 奇门遁甲盘图片路径
    - player_paths: 球员图片路径列表
    - title_lines: 标题文字行列表
    - today_str: 日期字符串，格式为 "YYYY-MM-DD"
    - output_filename: 输出文件名
    - output_dir: 输出文件夹
    - image_size: 最终输出图片的尺寸 (宽, 高)
    - font_path: 字体文件路径 (可选)
    - taiji_path: 太极图片路径 (可选)
    - fog_path: 雾气图片路径 (可选)
    - circle_path: 圆圈图片路径，用于叠加在指定格子上 (可选)
    - circle_cells: 要叠加圆圈的格子编号列表 (1-9)，九宫格编号：[[1,2,3],[4,5,6],[7,8,9]] (可选)
    - footer_path: 底部页脚图片路径，叠加在所有图层最上层 (可选)
    """
    
    # 确保输出目录存在
    os.makedirs(output_dir, exist_ok=True)

    def remove_background(image_path):
        """使用rembg移除图片背景"""
        try:
            with open(image_path, 'rb') as f:
                input_image = f.read()
            # 使用rembg移除背景
            output_image = remove(input_image)
            # 转换为PIL Image
            return Image.open(io.BytesIO(output_image)).convert("RGBA")
        except Exception as e:
            print(f"警告：移除背景失败，使用原图。路径：{image_path}，错误：{e}")
            # 如果失败，返回原图
            return Image.open(image_path).convert("RGBA")
    
    def remove_white_background(img, threshold=240):
        """移除白色背景，将其转换为透明"""
        # 确保图片是RGBA格式
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # 获取像素数据
        data = img.getdata()
        
        # 创建新的像素列表
        new_data = []
        for item in data:
            # 如果像素接近白色（RGB值都大于threshold），则设置为透明
            if item[0] > threshold and item[1] > threshold and item[2] > threshold:
                new_data.append((255, 255, 255, 0))  # 完全透明
            else:
                new_data.append(item)  # 保持原像素
        
        # 创建新图片
        img.putdata(new_data)
        return img
    
    def enhance_contrast(img, factor=1.5):
        """增强图片对比度，使文字和符号更清晰"""
        # 分离RGB和alpha通道
        if img.mode == "RGBA":
            rgb = img.convert("RGB")
            alpha = img.split()[3]
            # 增强对比度
            enhancer = ImageEnhance.Contrast(rgb)
            rgb_enhanced = enhancer.enhance(factor)
            # 合并回RGBA
            img = Image.merge("RGBA", (*rgb_enhanced.split(), alpha))
        else:
            # 如果不是RGBA，直接增强
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(factor)
        return img
    
    def enhance_sharpness(img, factor=2.0):
        """增强图片锐度，使边缘更清晰"""
        if img.mode == "RGBA":
            rgb = img.convert("RGB")
            alpha = img.split()[3]
            # 增强锐度
            enhancer = ImageEnhance.Sharpness(rgb)
            rgb_enhanced = enhancer.enhance(factor)
            # 合并回RGBA
            img = Image.merge("RGBA", (*rgb_enhanced.split(), alpha))
        else:
            enhancer = ImageEnhance.Sharpness(img)
            img = enhancer.enhance(factor)
        return img
    
    def enhance_qimen_image(img):
        """增强qimen图片清晰度：对比度 + 锐度"""
        img = enhance_contrast(img, factor=1.5)
        img = enhance_sharpness(img, factor=2.0)
        return img
    
    def crop_to_content(img):
        """裁剪图片，只保留非透明像素的区域"""
        # 确保图片是RGBA格式
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # 获取alpha通道
        alpha = img.split()[3]
        
        # 获取非透明像素的边界框
        bbox = alpha.getbbox()
        
        if bbox:
            # 裁剪到边界框
            return img.crop(bbox)
        else:
            # 如果没有非透明像素，返回原图
            return img
    
    def feather_edges(img, feather_radius=3):
        """为图片边缘添加羽化效果，使边缘更柔和"""
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        
        # 获取alpha通道
        alpha = img.split()[3]
        
        # 对alpha通道应用高斯模糊，创建羽化效果
        alpha_feathered = alpha.filter(ImageFilter.GaussianBlur(radius=feather_radius))
        
        # 合并回RGBA
        r, g, b = img.split()[:3]
        return Image.merge("RGBA", (r, g, b, alpha_feathered))
    
    def set_alpha(img, alpha_ratio):
        """设置图片的透明度（alpha_ratio: 0.0-1.0）"""
        if img.mode == "RGBA":
            r, g, b, a = img.split()
            a = a.point(lambda x: int(x * alpha_ratio))
            return Image.merge("RGBA", (r, g, b, a))
        return img
    
    def create_handwritten_text_image(text, font, text_color=(10, 10, 10), padding=50):
        """创建手写风格的文字图片"""
        # 测量文字大小
        temp_draw = ImageDraw.Draw(Image.new('RGBA', (1, 1)))
        bbox = temp_draw.textbbox((0, 0), text, font=font)
        text_width = bbox[2] - bbox[0]
        text_height = bbox[3] - bbox[1]
        
        # 创建临时画布
        temp_img = Image.new('RGBA', (text_width + padding * 2, text_height + padding * 2), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)
        
        # 绘制文字（单层，无粗体效果）
        temp_draw.text((padding, padding), text, font=font, fill=(*text_color, 255))
        
        return crop_to_content(temp_img)

    # 1. 加载背景图并裁剪到指定尺寸（保持宽高比，居中裁剪）
    try:
        bg_img = Image.open(bg_path).convert("RGBA")
        
        # 计算裁剪区域以保持宽高比
        bg_aspect = bg_img.width / bg_img.height
        target_aspect = image_size[0] / image_size[1]
        
        if bg_aspect > target_aspect:
            # 背景图更宽，需要裁剪宽度
            new_height = bg_img.height
            new_width = int(bg_img.height * target_aspect)
            left = (bg_img.width - new_width) // 2
            top = 0
        else:
            # 背景图更高，需要裁剪高度
            new_width = bg_img.width
            new_height = int(bg_img.width / target_aspect)
            left = 0
            top = (bg_img.height - new_height) // 2
        
        # 裁剪并调整大小
        background = bg_img.crop((left, top, left + new_width, top + new_height))
        background = background.resize(image_size, Image.LANCZOS)
    except FileNotFoundError:
        print(f"错误：背景图片未找到，路径：{bg_path}")
        return
    except Exception as e:
        print(f"加载或调整背景图片时出错：{e}")
        return

    # 2. 叠加太极图 - 放置在背景之上，但位于玩家和奇门图之下
    if taiji_path:
        try:
            taiji_img = Image.open(taiji_path).convert("RGBA")
            # 计算尺寸：35%的背景高度，保持宽高比
            taiji_height = int(image_size[1] * 0.35)
            aspect_ratio = taiji_img.width / taiji_img.height
            taiji_width = int(taiji_height * aspect_ratio)
            
            # 调整大小
            taiji_img = taiji_img.resize((taiji_width, taiji_height), Image.LANCZOS)
            
            # 调整透明度为30%
            taiji_img = set_alpha(taiji_img, 0.3)
            
            # 位置：水平居中，距离底部5%
            taiji_x = (image_size[0] - taiji_width) // 2
            taiji_y = image_size[1] - taiji_height - int(image_size[1] * 0.05)
            taiji_pos = (taiji_x, taiji_y)
            
            background.alpha_composite(taiji_img, taiji_pos)
        except FileNotFoundError:
            print(f"警告：太极图片未找到，跳过。路径：{taiji_path}")
        except Exception as e:
            print(f"加载或叠加太极图时出错：{e}")

    # 3. 叠加奇门遁甲盘 - 居中放置，50%宽度，保持正方形比例
    if qimen_path:
        try:
            qimen_plate = Image.open(qimen_path).convert("RGBA")
            # 移除白色背景
            qimen_plate = remove_white_background(qimen_plate)
            # 使用选择的增强方法提高清晰度
            qimen_plate = enhance_qimen_image(qimen_plate)
            # 计算尺寸：50%宽度，保持正方形
            qimen_size = int(image_size[0] * 0.5)
            # 保持原始宽高比，但限制在qimen_size内
            qimen_plate.thumbnail((qimen_size, qimen_size), Image.LANCZOS)
            # 居中放置，向上移动
            qimen_x = (image_size[0] - qimen_plate.width) // 2
            qimen_y = (image_size[1] - qimen_plate.height) // 2 - int(image_size[1] * 0.09)
            qimen_pos = (qimen_x, qimen_y)
            background.alpha_composite(qimen_plate, qimen_pos)
            
            # 3.5. 叠加雾气图 - 放置在qimen图上面，拉伸到与qimen图完全相同的尺寸
            if fog_path:
                try:
                    fog_img = Image.open(fog_path).convert("RGBA")
                    fog_img = fog_img.resize((qimen_plate.width, qimen_plate.height), Image.LANCZOS)
                    fog_img = set_alpha(fog_img, 0.5)
                    background.alpha_composite(fog_img, qimen_pos)
                except FileNotFoundError:
                    print(f"警告：雾气图片未找到，跳过。路径：{fog_path}")
                except Exception as e:
                    print(f"加载或叠加雾气图时出错：{e}")
            
            # 3.6. 叠加circle.png - 在手动指定的格子上叠加圆圈
            if circle_path and circle_cells:
                try:
                    # 加载circle图片一次，在循环外
                    circle_img_base = Image.open(circle_path).convert("RGBA")
                    
                    # 计算每个格子的大小（resize后的尺寸）
                    cell_width = qimen_plate.width // 3
                    cell_height = qimen_plate.height // 3
                    
                    # 计算circle的大小
                    base_circle_size = int(min(cell_width, cell_height) * 0.8)
                    circle_size = int(base_circle_size * 1.728)
                    
                    # 在每个指定的格子上叠加circle
                    # 九宫格编号：[[1,2,3],[4,5,6],[7,8,9]]
                    # 编号转索引：编号-1 = 内部索引(0-8)
                    for idx, cell_num in enumerate(circle_cells):
                        if 1 <= cell_num <= 9:
                            # 复制并调整大小到统一尺寸
                            circle_img = circle_img_base.copy()
                            circle_img = circle_img.resize((circle_size, circle_size), Image.LANCZOS)
                            
                            # 如果是第二个circle（索引1），旋转90度
                            if idx == 1:
                                circle_img = circle_img.rotate(-90, expand=True)
                                # 旋转后可能改变尺寸，确保恢复到相同大小
                                if circle_img.size != (circle_size, circle_size):
                                    circle_img = circle_img.resize((circle_size, circle_size), Image.LANCZOS)
                            
                            # 调整透明度至90%
                            circle_img = set_alpha(circle_img, 0.9)
                            
                            cell_idx = cell_num - 1  # 转换为0-8的索引
                            row = cell_idx // 3
                            col = cell_idx % 3
                            
                            # 计算格子在resize后的qimen图中的位置
                            cell_left = col * cell_width
                            cell_top = row * cell_height
                            
                            # 计算circle在背景图上的位置（居中在格子内）
                            circle_x = qimen_x + cell_left + (cell_width - circle_img.width) // 2
                            circle_y = qimen_y + cell_top + (cell_height - circle_img.height) // 2
                            circle_pos = (circle_x, circle_y)
                            
                            background.alpha_composite(circle_img, circle_pos)
                            rotation_info = "（旋转90度）" if idx == 1 else ""
                            print(f"在格子 {cell_num} (位置: row={row}, col={col}) 叠加圆圈{rotation_info}")
                        else:
                            print(f"警告：格子编号 {cell_num} 无效，应在1-9之间")
                except FileNotFoundError:
                    print(f"警告：圆圈图片未找到，跳过。路径：{circle_path}")
                except Exception as e:
                    print(f"叠加圆圈时出错：{e}")
        except FileNotFoundError:
            print(f"警告：奇门遁甲盘图片未找到，跳过。路径：{qimen_path}")
        except Exception as e:
            print(f"加载或叠加奇门遁甲盘时出错：{e}")

    # 4. 叠加球员图片 - 底部对齐，36%高度，左右各1%边距
    if player_paths:
        player_height = int(image_size[1] * 0.36)
        bottom_y = image_size[1] - player_height
        
        num_players = len(player_paths)
        
        for idx, player_path in enumerate(player_paths):
            try:
                # 使用rembg移除背景
                print(f"正在处理球员图片 {idx + 1}/{num_players}: {player_path}")
                player_img = remove_background(player_path)
                
                # 裁剪图片，只保留球员部分（移除透明边缘）
                player_img = crop_to_content(player_img)
                
                # 计算缩放比例，保持宽高比，高度限制为player_height
                aspect_ratio = player_img.width / player_img.height
                player_width = int(player_height * aspect_ratio)
                
                # 调整大小
                player_img = player_img.resize((player_width, player_height), Image.LANCZOS)
                
                # 为边缘添加羽化效果，使边缘更柔和
                player_img = feather_edges(player_img, feather_radius=5)
                
                # 计算x位置：Player 1在左边1%，Player 2在右边1%
                if idx == 0:
                    player_x = int(image_size[0] * 0.01)
                else:
                    player_x = int(image_size[0] * 0.99 - player_width)
                
                player_pos = (player_x, bottom_y)
                
                background.alpha_composite(player_img, player_pos)
            except FileNotFoundError:
                print(f"警告：球员图片未找到，跳过。路径：{player_path}")
            except Exception as e:
                print(f"加载或叠加球员图片时出错：{e}")

    # 5. 添加日期 - 左上角
    date_text = today_str
    date_font = ImageFont.load_default()
    date_text_img = create_handwritten_text_image(date_text, date_font, text_color=(10, 10, 10))
    
    # 缩放图片使日期大小约为标题的一半（标题字体70，日期约35）
    scale_factor = 3
    date_text_img = date_text_img.resize(
        (int(date_text_img.width * scale_factor), int(date_text_img.height * scale_factor)),
        Image.LANCZOS
    )
    
    # 位置：左上角，留出一些边距
    date_x = int(image_size[0] * 0.02)  # 距离左边2%
    date_y = int(image_size[1] * 0.02)  # 距离顶部2%
    
    # 绘制日期
    background.alpha_composite(date_text_img, (date_x, date_y))

    # 6. 添加标题文字 - 手写风格
    if title_lines:
        # 加载字体：优先使用STXINGKA.TTF（行楷字体）
        font_size = 70
        font = None
        
        # 1. 尝试使用指定的字体路径
        if font_path and os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
            except:
                pass
        
        # 2. 尝试加载STXINGKA.TTF
        if font is None:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            stxingka_path = os.path.join(script_dir, "assets", "STXINGKA.TTF")
            if os.path.exists(stxingka_path):
                try:
                    font = ImageFont.truetype(stxingka_path, font_size)
                except:
                    pass
        
        # 3. 使用默认字体
        if font is None:
            font = ImageFont.load_default()
        
        # 计算文字位置和绘制
        text_color = (10, 10, 10, 255)
        line_height = font_size + 10
        start_y = int(image_size[1] * 0.095)
        
        for line_idx, line_text in enumerate(title_lines):
            # 创建手写风格的文字图片
            text_img = create_handwritten_text_image(line_text, font, text_color=(10, 10, 10))
            
            # 计算位置并居中
            text_x = (image_size[0] - text_img.width) // 2
            text_y = start_y + line_idx * line_height
            
            # 绘制文字
            background.alpha_composite(text_img, (text_x, text_y))

    # 7. 叠加footer图片 - 底部，所有图层最上层
    if footer_path:
        try:
            footer_img = Image.open(footer_path).convert("RGBA")
            
            # 计算footer的宽度，为背景宽度的25%，保持宽高比
            footer_width = int(image_size[0] * 0.25)
            aspect_ratio = footer_img.height / footer_img.width
            footer_height = int(footer_width * aspect_ratio)
            
            # 调整footer大小
            footer_img = footer_img.resize((footer_width, footer_height), Image.LANCZOS)
            
            # 位置：底部对齐，水平居中，向上移动1%
            footer_x = (image_size[0] - footer_width) // 2
            footer_y = image_size[1] - footer_height - int(image_size[1] * 0.01)
            
            # 叠加footer（在所有图层最上层）
            background.alpha_composite(footer_img, (footer_x, footer_y))
        except FileNotFoundError:
            print(f"警告：footer图片未找到，跳过。路径：{footer_path}")
        except Exception as e:
            print(f"加载或叠加footer时出错：{e}")

    # 8. 保存图片
    output_path = os.path.join(output_dir, output_filename)
    background_rgb = Image.new("RGB", background.size, (255, 255, 255))
    background_rgb.paste(background, mask=background.split()[3] if background.mode == "RGBA" else None)
    background_rgb.save(output_path, quality=95)
    print(f"封面图已保存到: {output_path}")

def get_random_background(backgrounds_dir="backgrounds"):
    """随机选择一个背景文件（支持GCS路径）"""
    bg_files = list_gcs_files(backgrounds_dir)
    bg_files = [f for f in bg_files if f.startswith("bg_") and f.endswith(".png")]
    bg_file = random.choice(bg_files) if bg_files else "bg_001.png"
    print(f"随机选择背景: {bg_file}")
    
    # Return full path (GCS or local)
    if is_gcs_path(backgrounds_dir):
        from gcs_utils import get_gcs_path
        bucket = backgrounds_dir.replace("gs://", "").split("/")[0]
        return get_gcs_path(bucket, "backgrounds", bg_file)
    else:
        return os.path.join(backgrounds_dir, bg_file)

def get_player_paths(away_team, home_team, players_dir="players"):
    """根据队伍前缀自动查找球员图片并返回路径列表（支持GCS路径）"""
    player_files = list_gcs_files(players_dir)
    player_files = [f for f in player_files if f.endswith(".png")]
    
    # 查找 away_team 的球员图片
    away_player_files = [f for f in player_files if f.startswith(f"{away_team}_")]
    player1_file = random.choice(away_player_files) if away_player_files else None
    
    # 查找 home_team 的球员图片
    home_player_files = [f for f in player_files if f.startswith(f"{home_team}_")]
    player2_file = random.choice(home_player_files) if home_player_files else None
    
    if not player1_file:
        print(f"警告：未找到 {away_team} 的球员图片")
    if not player2_file:
        print(f"警告：未找到 {home_team} 的球员图片")
    
    if player1_file:
        print(f"找到客场球员图片: {player1_file}")
    if player2_file:
        print(f"找到主场球员图片: {player2_file}")
    
    # 构建球员路径列表（只包含找到的球员图片）
    player_paths = []
    if player1_file:
        if is_gcs_path(players_dir):
            from gcs_utils import get_gcs_path
            bucket = players_dir.replace("gs://", "").split("/")[0]
            player_paths.append(get_gcs_path(bucket, "players", player1_file))
        else:
            player_paths.append(os.path.join(players_dir, player1_file))
    if player2_file:
        if is_gcs_path(players_dir):
            from gcs_utils import get_gcs_path
            bucket = players_dir.replace("gs://", "").split("/")[0]
            player_paths.append(get_gcs_path(bucket, "players", player2_file))
        else:
            player_paths.append(os.path.join(players_dir, player2_file))
    
    return player_paths

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成NBA奇门球探风格封面图")
    parser.add_argument("--date", type=str, required=True, help="日期 (格式: YYYY-MM-DD, 例如: 2025-11-26)")
    parser.add_argument("--away-team", type=str, required=True, help="客场队伍代码 (例如: HOU)")
    parser.add_argument("--home-team", type=str, required=True, help="主场队伍代码 (例如: GSW)")
    parser.add_argument("--title", type=str, nargs="+", required=True, help="标题文字，多行用空格分隔，使用引号包裹")
    parser.add_argument("--circle-cells", type=int, nargs="+", default=[], help="要叠加圆圈的格子编号 (1-9)，多个用空格分隔 (例如: 2 4)")
    
    args = parser.parse_args()
    
    today_str = args.date
    away_team = args.away_team
    home_team = args.home_team
    title_lines = args.title
    circle_cells = args.circle_cells if args.circle_cells else []
    
    # 定义素材路径
    bg_file = get_random_background()
    qimen_file = f"{today_str}.jpg"
    
    # 根据队伍前缀自动查找球员图片
    player_paths = get_player_paths(away_team, home_team)

    # 完整路径（bg_file已经包含完整路径）
    bg_path = bg_file
    qimen_path = os.path.join("qimen", qimen_file)
    
    taiji_path = os.path.join("assets", "taiji.png")
    fog_path = os.path.join("assets", "fog.png")
    circle_path = os.path.join("assets", "circle-red.png")
    footer_path = os.path.join("assets", "footer.png")

    # 生成封面
    output_name = f"cover_{today_str}.jpg"
    generate_cover(
        bg_path=bg_path,
        qimen_path=qimen_path,
        player_paths=player_paths,
        title_lines=title_lines,
        today_str=today_str,
        output_filename=output_name,
        taiji_path=taiji_path,
        fog_path=fog_path,
        circle_path=circle_path,
        circle_cells=circle_cells,
        footer_path=footer_path
    )