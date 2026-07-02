# -*- coding: utf-8 -*-
"""
Created on Thu Jul  2 11:18:09 2026

@author: Tristan
"""

import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ─────────────────────────────────────────────
#  核心逻辑：多文件对比，提取公共段与可变段
# ─────────────────────────────────────────────

def get_pdf_files(folder):
    """获取文件夹内所有 PDF 文件名（排序后）"""
    return sorted(f for f in os.listdir(folder) if f.lower().endswith('.pdf'))


def split_name_core(filename):
    """去掉扩展名，返回核心名称"""
    return os.path.splitext(filename)[0]


def find_common_segments(names):
    """
    对多个文件名进行逐字符对比，提取公共前缀、公共后缀与各文件可变段。
    修正：公共前缀末尾若为数字或字母，则向左回退到最近的非数字非字母边界，
         避免将年份、编号等可变内容的公共开头误归入前缀。
    """
    if not names:
        return "", "", []

    # ── 找公共前缀
    prefix = names[0]
    for name in names[1:]:
        i = 0
        while i < len(prefix) and i < len(name) and prefix[i] == name[i]:
            i += 1
        prefix = prefix[:i]

    # ── 修正：前缀末尾不能以数字或ASCII字母结尾（回退到语义边界）
    end = len(prefix)
    while end > 0 and (prefix[end - 1].isdigit() or prefix[end - 1].isascii() and prefix[end - 1].isalpha()):
        end -= 1
    prefix = prefix[:end]

    # ── 找公共后缀（在去掉前缀后的部分中找）
    stripped = [name[len(prefix):] for name in names]
    suffix = stripped[0]
    for s in stripped[1:]:
        j = 0
        while j < len(suffix) and j < len(s) and suffix[-(j + 1)] == s[-(j + 1)]:
            j += 1
        suffix = suffix[-j:] if j > 0 else ""

    # ── 同理修正后缀：开头不能以数字或ASCII字母开头
    start = 0
    while start < len(suffix) and (suffix[start].isdigit() or suffix[start].isascii() and suffix[start].isalpha()):
        start += 1
    suffix = suffix[start:]

    # ── 提取各文件可变段
    variables = []
    for name in names:
        mid_start = len(prefix)
        mid_end = len(name) - len(suffix) if suffix else len(name)
        variables.append(name[mid_start:mid_end])

    return prefix, suffix, variables



def build_template_display(prefix, suffix, variables):
    """
    生成供显示的命名规则模板字符串。
    示例：{泸州老窖：}【2003年/2004年/...】{年度报告}
    只展示前3个可变值作为示例。
    """
    sample_vars = "/".join(variables[:3])
    if len(variables) > 3:
        sample_vars += "/..."

    parts = []
    if prefix:
        parts.append(f"{{{prefix}}}")
    if variables:
        parts.append(f"【{sample_vars}】")
    if suffix:
        parts.append(f"{{{suffix}}}")

    return "  +  ".join(parts) if parts else "（无法拆解）"


def build_new_name(new_prefix, new_suffix, variable, ext):
    """
    用新的前缀/后缀替换原公共部分，保留可变部分不变。
    new_prefix / new_suffix 均可为空字符串。
    """
    return new_prefix + variable + new_suffix + ext


# ─────────────────────────────────────────────
#  GUI 主应用
# ─────────────────────────────────────────────

class RenameApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("批量文件重命名工具")
        self.resizable(True, True)
        self.minsize(860, 620)

        # 分析结果缓存
        self._common_prefix = ""
        self._common_suffix = ""
        self._variables = []       # 每个文件的可变中间部分
        self._all_files = []       # 全部 PDF 文件名
        self._plan = []            # 重命名计划 [(old, new), ...]

        self._build_ui()

    # ── 界面构建 ──────────────────────────────

    def _build_ui(self):
        # 顶部：文件夹选择
        frm_top = tk.LabelFrame(self, text=" 📁 目标文件夹 ", font=("微软雅黑", 10, "bold"))
        frm_top.pack(fill="x", padx=14, pady=(14, 4))

        self.var_folder = tk.StringVar()
        tk.Entry(frm_top, textvariable=self.var_folder, font=("微软雅黑", 10),
                 state="readonly").pack(side="left", fill="x", expand=True, padx=(10, 6), pady=8)
        tk.Button(frm_top, text="选择文件夹", command=self._choose_folder,
                  font=("微软雅黑", 10)).pack(side="left", padx=(0, 10), pady=8)

        # 中部：命名格式配置
        frm_info = tk.LabelFrame(self, text=" 📋 命名格式配置 ", font=("微软雅黑", 10, "bold"))
        frm_info.pack(fill="x", padx=14, pady=4)
        frm_info.columnconfigure(1, weight=1)

        # ── 识别到的命名规则（只读，自动分析）
        tk.Label(frm_info, text="识别到的命名规则：", font=("微软雅黑", 10), anchor="w"
                 ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.var_rule_display = tk.StringVar(value="（选择文件夹后自动分析）")
        tk.Entry(frm_info, textvariable=self.var_rule_display, font=("微软雅黑", 9),
                 state="readonly", fg="#1a6fbf",
                 readonlybackground="#eef4fb"
                 ).grid(row=0, column=1, sticky="ew", padx=(0, 10), pady=(10, 4))

        # ── 公共前缀修改框
        tk.Label(frm_info, text="修改公共前缀为：", font=("微软雅黑", 10), anchor="w"
                 ).grid(row=1, column=0, sticky="w", padx=10, pady=4)
        self.var_new_prefix = tk.StringVar()
        self.var_new_prefix.trace_add("write", self._on_format_change)
        tk.Entry(frm_info, textvariable=self.var_new_prefix, font=("微软雅黑", 10)
                 ).grid(row=1, column=1, sticky="ew", padx=(0, 10), pady=4)

        # ── 公共后缀修改框
        tk.Label(frm_info, text="修改公共后缀为：", font=("微软雅黑", 10), anchor="w"
                 ).grid(row=2, column=0, sticky="w", padx=10, pady=4)
        self.var_new_suffix = tk.StringVar()
        self.var_new_suffix.trace_add("write", self._on_format_change)
        tk.Entry(frm_info, textvariable=self.var_new_suffix, font=("微软雅黑", 10)
                 ).grid(row=2, column=1, sticky="ew", padx=(0, 10), pady=4)

        # 格式说明
        hint = (
            "说明：{}内为公共部分（所有文件相同），【】内为可变部分（每个文件不同，重命名时保持不变）\n"
            "仅修改前缀/后缀输入框，可变部分自动保留。两个框均可留空。"
        )
        tk.Label(frm_info, text=hint, font=("微软雅黑", 9), fg="#888888",
                 anchor="w", justify="left"
                 ).grid(row=3, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))

        # 预览列表
        frm_list = tk.LabelFrame(self, text=" 🔍 重命名预览 ", font=("微软雅黑", 10, "bold"))
        frm_list.pack(fill="both", expand=True, padx=14, pady=4)

        cols = ("原文件名", "修改后文件名")
        self.tree = ttk.Treeview(frm_list, columns=cols, show="headings", height=12)
        for col in cols:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=390, anchor="w")

        vsb = ttk.Scrollbar(frm_list, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(8, 0), pady=8)
        vsb.pack(side="right", fill="y", pady=8, padx=(0, 8))

        # 底部：状态 + 按钮
        frm_bot = tk.Frame(self)
        frm_bot.pack(fill="x", padx=14, pady=(4, 14))

        self.lbl_status = tk.Label(frm_bot, text="请先选择文件夹。",
                                   font=("微软雅黑", 9), fg="#666666", anchor="w")
        self.lbl_status.pack(side="left", fill="x", expand=True)

        tk.Button(frm_bot, text="批量修改", command=self._execute_rename,
                  font=("微软雅黑", 11, "bold"), bg="#4a90d9", fg="white",
                  activebackground="#357abd", relief="flat",
                  padx=20, pady=6).pack(side="right")

    # ── 事件处理 ──────────────────────────────

    def _choose_folder(self):
        folder = filedialog.askdirectory(title="选择包含 PDF 文件的文件夹")
        if not folder:
            return
        self.var_folder.set(folder)
        self._load_folder(folder)

    def _load_folder(self, folder):
        """加载文件夹：读取全部 PDF，对比分析公共/可变部分"""
        self._all_files = get_pdf_files(folder)

        if not self._all_files:
            self.var_rule_display.set("未找到 PDF 文件")
            self.lbl_status.config(text="该文件夹内没有 PDF 文件。")
            return

        # 去扩展名后进行对比分析
        cores = [split_name_core(f) for f in self._all_files]
        prefix, suffix, variables = find_common_segments(cores)

        self._common_prefix = prefix
        self._common_suffix = suffix
        self._variables = variables

        # 显示识别规则
        self.var_rule_display.set(build_template_display(prefix, suffix, variables))

        # 预填修改框（默认保留原值，方便用户在此基础上修改）
        self.var_new_prefix.set(prefix)
        self.var_new_suffix.set(suffix)

        self.lbl_status.config(
            text=f"已加载 {len(self._all_files)} 个文件，自动识别公共前缀「{prefix}」、公共后缀「{suffix}」。"
        )
        self._refresh_preview()

    def _on_format_change(self, *_):
        self._refresh_preview()

    def _refresh_preview(self):
        """实时刷新预览列表"""
        for row in self.tree.get_children():
            self.tree.delete(row)
        self._plan.clear()

        folder = self.var_folder.get()
        if not folder or not self._all_files:
            return

        new_prefix = self.var_new_prefix.get()   # 不 strip，保留用户空格
        new_suffix = self.var_new_suffix.get()

        for fname, variable in zip(self._all_files, self._variables):
            _, ext = os.path.splitext(fname)
            new_name = build_new_name(new_prefix, new_suffix, variable, ext)

            # 若新旧相同则标灰提示
            if new_name == fname:
                self.tree.insert("", "end", values=(fname, f"{new_name}（无变化）"),
                                 tags=("same",))
            else:
                self._plan.append((fname, new_name))
                self.tree.insert("", "end", values=(fname, new_name))

        self.tree.tag_configure("same", foreground="#bbbbbb")

        self.lbl_status.config(
            text=f"预览：{len(self._plan)} 个文件将被重命名，"
                 f"{len(self._all_files) - len(self._plan)} 个无变化将跳过。"
        )

    def _execute_rename(self):
        """执行批量重命名"""
        folder = self.var_folder.get()

        if not folder:
            messagebox.showwarning("提示", "请先选择目标文件夹。")
            return
        if not self._plan:
            messagebox.showinfo("提示", "没有需要重命名的文件（所有文件名均无变化）。")
            return

        confirm = messagebox.askyesno(
            "确认执行",
            f"即将重命名 {len(self._plan)} 个文件，此操作不可撤销，是否继续？"
        )
        if not confirm:
            return

        success, skipped = 0, []
        for old_name, new_name in self._plan:
            old_path = os.path.join(folder, old_name)
            new_path = os.path.join(folder, new_name)
            if os.path.exists(new_path) and old_name != new_name:
                skipped.append(f"{old_name}（目标文件名已存在）")
                continue
            try:
                os.rename(old_path, new_path)
                success += 1
            except Exception as e:
                skipped.append(f"{old_name}（错误：{e}）")

        # 重新加载刷新
        self._load_folder(folder)

        result_msg = f"完成！成功重命名 {success} 个文件。"
        if skipped:
            result_msg += f"\n\n跳过 {len(skipped)} 个：\n" + "\n".join(f"  • {f}" for f in skipped)
        messagebox.showinfo("执行结果", result_msg)


# ─────────────────────────────────────────────
#  入口
# ─────────────────────────────────────────────

if __name__ == "__main__":
    app = RenameApp()
    app.mainloop()
