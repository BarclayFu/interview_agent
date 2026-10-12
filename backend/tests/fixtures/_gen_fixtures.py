"""一次性生成测试用文字型 PDF（含中文，需内置 CJK 字体 china-s）。
用法：cd backend && uv run python tests/fixtures/_gen_fixtures.py
"""

import pymupdf

LINES = [
    "张三",
    "高级后端工程师 / 6 年经验",
    "联系方式：zhangsan@example.com",
    "",
    "项目经验",
    "项目一：订单系统重构（2023.03 - 2024.01）",
    "职责：后端负责人，负责订单链路拆分、库存扣减一致性、消息队列削峰。",
    "技术栈：Python / PostgreSQL / Redis / Kafka",
    "成果：峰值 QPS 从 800 提升到 2400，超时率从 2% 降到 0.1%。",
    "",
    "项目二：支付网关（2021.06 - 2023.02）",
    "职责：核心开发，负责多渠道支付路由与对账系统。",
    "技术栈：Go / MySQL / Redis",
    "成果：日处理订单 500 万笔，对账差错率低于百万分之一。",
]


def main() -> None:
    doc = pymupdf.open()
    page = doc.new_page()
    y = 72
    for line in LINES:
        if line:
            page.insert_text((72, y), line, fontname="china-s", fontsize=11)
        y += 18
    doc.save("tests/fixtures/resume_text.pdf")
    doc.close()
    print("fixtures written")


if __name__ == "__main__":
    main()
