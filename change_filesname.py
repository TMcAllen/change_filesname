import os
import re

# 目标目录
folder_path = r"D:\资料\研究资料\公司研究\行业公司\1-黄金珠宝行业\个股资料\A股\605599-菜百股份\年度报告"

def strip_original_prefix(filename):
    """剥离原始冗余前缀，返回核心文件名（如 '2024年年度报告.pdf'）"""
    # 匹配：日期-代码.交易所-简称-代码+全称
    pattern = r'^\d{4}-\d{2}-\d{2}-\d+\.[A-Z]+-[\u4e00-\u9fa5A-Za-z0-9]+-\d+[\u4e00-\u9fa5A-Za-z0-9（）()]+?(?=\d{4}年|北京)'
    match = re.search(pattern, filename)
    if match:
        return filename[match.end():]

    # 备用：截取"有限公司"之后的内容
    alt_match = re.search(r'(?<=有限公司)', filename)
    if alt_match:
        return filename[alt_match.end():]

    return None  # 无法识别前缀，跳过


def preview_rename(folder, new_prefix):
    """预览重命名结果，返回待处理列表"""
    plan = []
    for filename in sorted(os.listdir(folder)):
        if not filename.lower().endswith('.pdf'):
            continue
        core = strip_original_prefix(filename)
        if core is None:
            print(f"[无法识别] {filename}")
            continue
        new_filename = new_prefix + core
        plan.append((filename, new_filename))
        print(f"  {filename}")
        print(f"    → {new_filename}")
    return plan


def execute_rename(folder, plan):
    """执行重命名"""
    success, skipped = 0, []
    for old_name, new_name in plan:
        old_path = os.path.join(folder, old_name)
        new_path = os.path.join(folder, new_name)
        if os.path.exists(new_path) and old_name != new_name:
            print(f"[跳过-冲突] {new_name} 已存在")
            skipped.append(old_name)
            continue
        os.rename(old_path, new_path)
        success += 1
    print(f"\n完成！重命名 {success} 个，跳过 {len(skipped)} 个。")
    if skipped:
        for f in skipped:
            print(f"  跳过: {f}")


if __name__ == "__main__":
    print("=" * 60)
    print("批量重命名工具 - 菜百股份报告文件")
    print("=" * 60)

    # 第一步：输入新前缀
    print("\n请输入重命名后的文件名前缀（可留空表示无前缀）")
    print("示例：'605599-菜百股份-' 或 '菜百股份_' 或直接回车留空")
    new_prefix = input("新前缀：").strip()

    # 第二步：预览
    print(f"\n【预览】新前缀为：「{new_prefix}」")
    print("-" * 60)
    plan = preview_rename(folder_path, new_prefix)

    if not plan:
        print("没有找到可处理的文件，程序退出。")
        exit()

    # 第三步：确认执行
    print("-" * 60)
    confirm = input(f"\n共 {len(plan)} 个文件将被重命名，确认执行？(y/n)：").strip().lower()
    if confirm == 'y':
        execute_rename(folder_path, plan)
    else:
        print("已取消，未做任何修改。")
