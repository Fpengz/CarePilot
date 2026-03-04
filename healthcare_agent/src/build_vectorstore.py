"""
知识源向量化脚本 - NUS-Synapxe-IMDA AI Innovation Challenge 2026
负责人: Meng Dian
功能: 将所有知识源数据转化为向量，存储到 ChromaDB，供 RAG 检索 Tool (师湘淇) 使用

使用方法:
    pip install -r requirements.txt
    python scripts/build_vectorstore.py

输出:
    ./vectorstore/chroma_db/ — ChromaDB 持久化目录，师湘淇的 RAG Tool 直接加载此目录即可
"""

import json
import os
import re
import hashlib
import subprocess
from pathlib import Path

try:
    import chromadb
    from chromadb.config import Settings
except ImportError:
    print("请先安装 chromadb: pip install chromadb")
    raise

try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("请先安装 sentence-transformers: pip install sentence-transformers")
    raise


# ============================================================
# 配置
# ============================================================
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
VECTORSTORE_DIR = BASE_DIR / "vectorstore" / "chroma_db"

# Embedding 模型 — 使用 BGE-M3 (多语言，支持中英马来泰米尔)
# 也可以替换为 SEA-LION embedding（如果比赛提供）
EMBEDDING_MODEL = "BAAI/bge-m3"

# ACE PDF 目录
ACE_PDF_DIR = DATA_DIR / "clinical" / "ace_pdfs"

# ChromaDB Collection 名称
COLLECTIONS = {
    "drugs": "drug_knowledge",
    "food": "food_knowledge",
    "emotion": "emotion_support",
    "ace_guidelines": "ace_guidelines",
}


# ============================================================
# 数据加载 & 文档切片
# ============================================================

def load_json(filepath: str) -> dict | list:
    """加载 JSON 文件"""
    with open(filepath, "r", encoding="utf-8") as f:
        return json.load(f)


def generate_doc_id(text: str) -> str:
    """生成文档唯一ID"""
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def chunk_drug_data(drug: dict) -> list[dict]:
    """
    将一个药物条目切分为多个文档 chunk，每个 chunk 聚焦不同方面。
    这样 RAG 检索时能更精准匹配用户问题。
    """
    chunks = []
    drug_name = drug["drug_name_en"]
    drug_name_cn = drug["drug_name_cn"]
    drug_id = drug["drug_id"]

    # Chunk 1: 基本信息
    basic_info = (
        f"药物名称: {drug_name} ({drug_name_cn})\n"
        f"药物类别: {drug.get('drug_class', '')} ({drug.get('drug_class_cn', '')})\n"
        f"适应症: {drug.get('indication', '')} ({drug.get('indication_cn', '')})\n"
        f"品牌名: {', '.join(drug.get('brand_names', []))}\n"
        f"是否一线用药: {'是' if drug.get('is_first_line') else '否'}\n"
        f"新加坡补贴: {drug.get('singapore_subsidy', '')}\n"
        f"特别说明: {drug.get('special_notes', '')}"
    )
    chunks.append({
        "text": basic_info,
        "metadata": {
            "drug_id": drug_id,
            "drug_name": drug_name,
            "drug_name_cn": drug_name_cn,
            "chunk_type": "drug_basic_info",
            "source": "drug_database",
            "language": "multilingual",
        }
    })

    # Chunk 2: 剂量与用法
    dosage = drug.get("dosage", {})
    timing = drug.get("timing", {})
    dosage_info = (
        f"{drug_name} ({drug_name_cn}) 剂量与用法:\n"
        f"初始剂量: {dosage.get('initial', '')}\n"
        f"维持剂量: {dosage.get('maintenance', '')}\n"
        f"最大日剂量: {dosage.get('max_daily', '')}\n"
        f"调整方式: {dosage.get('titration', '')}\n"
        f"服药时间: {timing.get('relation_to_meal_cn', '')} — {timing.get('relation_to_meal_en', '')}\n"
        f"原因: {timing.get('reason', '')}\n"
        f"频率: {drug.get('frequency_cn', '')}"
    )
    chunks.append({
        "text": dosage_info,
        "metadata": {
            "drug_id": drug_id,
            "drug_name": drug_name,
            "drug_name_cn": drug_name_cn,
            "chunk_type": "drug_dosage",
            "meal_timing": timing.get("relation_to_meal", ""),
            "source": "drug_database",
        }
    })

    # Chunk 3: 用药提醒模板（给梁敬林的提醒Tool用）
    templates = drug.get("reminder_templates", {})
    if templates:
        reminder_texts = []
        for key, val in templates.items():
            if val:
                reminder_texts.append(f"{key}: {val}")
        if reminder_texts:
            reminder_info = (
                f"{drug_name} ({drug_name_cn}) 用药提醒模板:\n"
                + "\n".join(reminder_texts)
            )
            chunks.append({
                "text": reminder_info,
                "metadata": {
                    "drug_id": drug_id,
                    "drug_name": drug_name,
                    "drug_name_cn": drug_name_cn,
                    "chunk_type": "drug_reminder_template",
                    "meal_timing": timing.get("relation_to_meal", ""),
                    "source": "drug_database",
                }
            })

    # Chunk 4: 副作用与禁忌
    side_effects = drug.get("side_effects", {})
    contraindications = drug.get("contraindications", [])
    safety_info = (
        f"{drug_name} ({drug_name_cn}) 安全信息:\n"
        f"常见副作用: {', '.join(side_effects.get('common', []))}\n"
        f"严重副作用: {', '.join(side_effects.get('serious', []))}\n"
        f"禁忌症: {', '.join(contraindications)}\n"
        f"食物相互作用: {', '.join(drug.get('food_interactions', []))}"
    )
    chunks.append({
        "text": safety_info,
        "metadata": {
            "drug_id": drug_id,
            "drug_name": drug_name,
            "drug_name_cn": drug_name_cn,
            "chunk_type": "drug_safety",
            "source": "drug_database",
        }
    })

    # Chunk 5: 监测指标
    monitoring = drug.get("monitoring", {})
    if monitoring:
        monitor_info = (
            f"{drug_name} ({drug_name_cn}) 监测要求:\n"
            f"监测参数: {', '.join(monitoring.get('parameters', []))}\n"
            f"目标: {monitoring.get('hba1c_target', monitoring.get('bp_target', monitoring.get('ldl_target', '')))}\n"
            f"监测频率: {monitoring.get('frequency', '')}"
        )
        chunks.append({
            "text": monitor_info,
            "metadata": {
                "drug_id": drug_id,
                "drug_name": drug_name,
                "drug_name_cn": drug_name_cn,
                "chunk_type": "drug_monitoring",
                "source": "drug_database",
            }
        })

    return chunks


def chunk_food_data(food: dict) -> list[dict]:
    """将一个食物条目切分为多个 chunk"""
    chunks = []
    food_name = food["food_name_en"]
    food_name_cn = food["food_name_cn"]
    food_id = food["food_id"]

    # Chunk 1: 基本营养信息
    nutrition = food.get("nutrition_per_serving", {})
    basic_info = (
        f"食物: {food_name} ({food_name_cn})\n"
        f"马来名: {food.get('food_name_malay', '')}\n"
        f"菜系: {food.get('cuisine', '')}\n"
        f"来源: {food.get('source', '')}\n"
        f"份量: {food.get('serving_size', '')}\n"
        f"热量: {nutrition.get('calories_kcal', '')} kcal\n"
        f"碳水化合物: {nutrition.get('carbohydrates_g', '')}g\n"
        f"蛋白质: {nutrition.get('protein_g', '')}g\n"
        f"总脂肪: {nutrition.get('total_fat_g', '')}g\n"
        f"饱和脂肪: {nutrition.get('saturated_fat_g', '')}g\n"
        f"钠: {nutrition.get('sodium_mg', '')}mg\n"
        f"糖: {nutrition.get('sugar_g', '')}g\n"
        f"升糖指数(GI): {food.get('glycemic_index', '')} ({food.get('gi_value', '')})\n"
        f"健康标签: {', '.join(food.get('health_tags', []))}"
    )
    chunks.append({
        "text": basic_info,
        "metadata": {
            "food_id": food_id,
            "food_name": food_name,
            "food_name_cn": food_name_cn,
            "chunk_type": "food_nutrition",
            "cuisine": food.get("cuisine", ""),
            "gi_level": food.get("glycemic_index", ""),
            "source": "food_database",
        }
    })

    # Chunk 2-4: 各疾病的饮食建议
    disease_advice = food.get("disease_advice", {})
    for disease, advice in disease_advice.items():
        advice_text = (
            f"{food_name} ({food_name_cn}) 对{disease}患者的建议:\n"
            f"风险等级: {advice.get('risk_level', '')}\n"
            f"建议(中文): {advice.get('cn', '')}\n"
            f"建议(英文): {advice.get('en', '')}"
        )
        chunks.append({
            "text": advice_text,
            "metadata": {
                "food_id": food_id,
                "food_name": food_name,
                "food_name_cn": food_name_cn,
                "chunk_type": f"food_advice_{disease}",
                "disease": disease,
                "risk_level": advice.get("risk_level", ""),
                "source": "food_database",
            }
        })

    # Chunk 5: 更健康的替代选择
    alternatives = food.get("healthier_alternatives", [])
    if alternatives:
        alt_texts = [f"- {a['name_cn']} ({a['name_en']}): {a['benefit']}" for a in alternatives]
        alt_info = (
            f"{food_name} ({food_name_cn}) 更健康的替代选择:\n"
            + "\n".join(alt_texts)
        )
        chunks.append({
            "text": alt_info,
            "metadata": {
                "food_id": food_id,
                "food_name": food_name,
                "food_name_cn": food_name_cn,
                "chunk_type": "food_alternatives",
                "source": "food_database",
            }
        })

    return chunks


def chunk_clinical_data(clinical_data: dict) -> list[dict]:
    """将临床知识数据切分为 chunks"""
    chunks = []

    for disease_key, disease_data in clinical_data.items():
        if disease_key == "comorbidity_notes":
            # 合并症说明
            for combo_key, combo_data in disease_data.items():
                text = (
                    f"合并症说明 - {combo_key}:\n"
                    f"中文: {combo_data.get('cn', '')}\n"
                    f"英文: {combo_data.get('en', '')}"
                )
                chunks.append({
                    "text": text,
                    "metadata": {
                        "chunk_type": "comorbidity",
                        "diseases": combo_key,
                        "source": "clinical_guidelines",
                    }
                })
            continue

        disease_name = disease_data.get("disease_name_cn", disease_key)

        # Chunk: 疾病概述
        overview = (
            f"疾病: {disease_data.get('disease_name_en', '')} ({disease_name})\n"
            f"描述: {disease_data.get('description_cn', '')}\n"
            f"英文描述: {disease_data.get('description_en', '')}\n"
            f"新加坡患病率: {disease_data.get('prevalence_singapore', '')}"
        )
        chunks.append({
            "text": overview,
            "metadata": {
                "disease": disease_key,
                "chunk_type": "disease_overview",
                "source": "clinical_guidelines",
            }
        })

        # Chunk: 诊断标准
        diag = disease_data.get("diagnostic_criteria", {})
        if diag:
            diag_items = [f"{k}: {v}" for k, v in diag.items()]
            diag_text = (
                f"{disease_name} 诊断标准:\n"
                + "\n".join(diag_items)
            )
            chunks.append({
                "text": diag_text,
                "metadata": {
                    "disease": disease_key,
                    "chunk_type": "diagnostic_criteria",
                    "source": "clinical_guidelines",
                }
            })

        # Chunk: 监测阈值和行动建议
        thresholds = disease_data.get("monitoring_thresholds", {})
        for metric_name, metric_data in thresholds.items():
            actions = metric_data.get("actions", {})
            action_texts = []
            for level, action in actions.items():
                cn_action = action.get("cn", "") if isinstance(action, dict) else str(action)
                en_action = action.get("en", "") if isinstance(action, dict) else ""
                action_texts.append(f"[{level}] 中文: {cn_action}")
                if en_action:
                    action_texts.append(f"[{level}] English: {en_action}")

            threshold_text = (
                f"{disease_name} - {metric_name} 监测阈值与行动建议:\n"
                f"单位: {metric_data.get('unit', '')}\n"
                + "\n".join(action_texts)
            )
            chunks.append({
                "text": threshold_text,
                "metadata": {
                    "disease": disease_key,
                    "metric": metric_name,
                    "chunk_type": "monitoring_threshold",
                    "source": "clinical_guidelines",
                }
            })

        # Chunk: 生活方式建议
        lifestyle = disease_data.get("general_lifestyle_advice", {})
        if lifestyle:
            diet_cn = lifestyle.get("diet_cn", [])
            exercise_cn = lifestyle.get("exercise_cn", [])
            lifestyle_text = (
                f"{disease_name} 生活方式建议:\n"
                f"饮食建议:\n" + "\n".join(f"- {d}" for d in diet_cn) + "\n"
                f"运动建议:\n" + "\n".join(f"- {e}" for e in exercise_cn)
            )
            chunks.append({
                "text": lifestyle_text,
                "metadata": {
                    "disease": disease_key,
                    "chunk_type": "lifestyle_advice",
                    "source": "clinical_guidelines",
                }
            })

        # Chunk: 并发症
        complications = disease_data.get("complications_to_monitor", [])
        if complications:
            comp_texts = [f"- {c['name_cn']} ({c['name_en']}): {c['screening']}" for c in complications]
            comp_text = (
                f"{disease_name} 需监测的并发症:\n"
                + "\n".join(comp_texts)
            )
            chunks.append({
                "text": comp_text,
                "metadata": {
                    "disease": disease_key,
                    "chunk_type": "complications",
                    "source": "clinical_guidelines",
                }
            })

    return chunks


def chunk_emotion_data(emotion_data: dict) -> list[dict]:
    """将情绪支持数据切分为 chunks"""
    chunks = []

    detection = emotion_data.get("emotion_detection", {})

    # Chunk: 情绪关键词（按语言）
    keywords = detection.get("negative_emotion_keywords", {})
    for lang, categories in keywords.items():
        for category, words in categories.items():
            kw_text = (
                f"情绪关键词 - 语言:{lang}, 类别:{category}\n"
                f"关键词: {', '.join(words)}"
            )
            chunks.append({
                "text": kw_text,
                "metadata": {
                    "chunk_type": "emotion_keywords",
                    "language": lang,
                    "emotion_category": category,
                    "source": "emotion_support",
                }
            })

    # Chunk: 情绪回应模板
    templates = detection.get("response_templates", {})
    for template_key, template_data in templates.items():
        template_texts = [f"{lang}: {text}" for lang, text in template_data.items()]
        template_text = (
            f"情绪回应模板 - {template_key}:\n"
            + "\n".join(template_texts)
        )
        chunks.append({
            "text": template_text,
            "metadata": {
                "chunk_type": "emotion_response",
                "template_type": template_key,
                "source": "emotion_support",
            }
        })

    # Chunk: 主动关怀模板
    proactive = detection.get("proactive_check_in_templates", {})
    for check_key, check_data in proactive.items():
        if isinstance(check_data, dict) and "cn" in check_data:
            check_text = (
                f"主动关怀模板 - {check_key}:\n"
                f"中文: {check_data.get('cn', '')}\n"
                f"英文: {check_data.get('en', '')}"
            )
            chunks.append({
                "text": check_text,
                "metadata": {
                    "chunk_type": "proactive_checkin",
                    "checkin_type": check_key,
                    "source": "emotion_support",
                }
            })

    # Chunk: 心理健康资源
    resources = emotion_data.get("singapore_mental_health_resources", [])
    if resources:
        resource_texts = [
            f"- {r['name']} ({r.get('name_cn', '')}): {r['hotline']} — {r.get('description', '')} [{r.get('hours', '')}]"
            for r in resources
        ]
        resource_text = (
            "新加坡心理健康援助资源:\n"
            + "\n".join(resource_texts)
        )
        chunks.append({
            "text": resource_text,
            "metadata": {
                "chunk_type": "mental_health_resources",
                "source": "emotion_support",
            }
        })

    return chunks


def chunk_drinks_data(drinks_data: dict) -> list[dict]:
    """将饮品数据切分为 chunks"""
    chunks = []

    # Kopitiam 饮品术语
    terminology = drinks_data.get("kopitiam_drink_guide", {}).get("terminology", {})
    for drink_name, drink_info in terminology.items():
        drink_text = (
            f"新加坡饮品: {drink_name}\n"
            f"中文: {drink_info.get('cn', '')}\n"
            f"英文: {drink_info.get('en', '')}\n"
            f"热量: {drink_info.get('calories', 'N/A')} kcal\n"
            f"糖分: {drink_info.get('sugar_g', 'N/A')}g"
        )
        if "note" in drink_info:
            drink_text += f"\n备注: {drink_info['note']}"
        chunks.append({
            "text": drink_text,
            "metadata": {
                "chunk_type": "drink_info",
                "drink_name": drink_name,
                "source": "food_database",
            }
        })

    # 糖尿病饮品建议
    recs = drinks_data.get("kopitiam_drink_guide", {}).get("diabetes_recommendations", {})
    if recs:
        rec_text = (
            "糖尿病患者饮品建议:\n"
            f"推荐: {', '.join(recs.get('best_choices', []))}\n"
            f"可接受: {', '.join(recs.get('acceptable', []))}\n"
            f"限制: {', '.join(recs.get('limit', []))}\n"
            f"避免: {', '.join(recs.get('avoid', []))}"
        )
        chunks.append({
            "text": rec_text,
            "metadata": {
                "chunk_type": "drink_recommendation",
                "disease": "diabetes",
                "source": "food_database",
            }
        })

    # 本地点餐Tips
    tips = drinks_data.get("local_food_ordering_tips", {}).get("useful_phrases", {})
    if tips:
        tip_texts = [f"- {v.get('cn', '')} ({v.get('en', '')})" for v in tips.values()]
        tips_text = (
            "新加坡小贩中心健康点餐常用语:\n"
            + "\n".join(tip_texts)
        )
        chunks.append({
            "text": tips_text,
            "metadata": {
                "chunk_type": "ordering_tips",
                "source": "food_database",
            }
        })

    return chunks


# ============================================================
# PDF 数据加载 & 文档切片
# ============================================================

def extract_pdf_text(pdf_path: str) -> str:
    """用 pdftotext 提取 PDF 文本"""
    try:
        result = subprocess.run(
            ["pdftotext", pdf_path, "-"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            return result.stdout
    except FileNotFoundError:
        print("    警告: pdftotext 未安装，请运行 brew install poppler")
    except subprocess.TimeoutExpired:
        print(f"    警告: PDF 提取超时: {pdf_path}")
    return ""


def detect_pdf_topic(filename: str, text_preview: str) -> str:
    """根据文件名和内容判断 PDF 主题"""
    fname = filename.lower()
    if "t2dm" in fname or "diabetes" in fname:
        return "t2dm"
    if "lipid" in fname:
        return "lipids"
    if "hypertension" in fname or "blood_pressure" in fname:
        return "hypertension"
    # 从内容判断
    preview = text_preview[:500].lower()
    if "diabetes" in preview or "t2dm" in preview or "hba1c" in preview:
        return "t2dm"
    if "lipid" in preview or "cholesterol" in preview or "statin" in preview:
        return "lipids"
    if "hypertension" in preview or "blood pressure" in preview:
        return "hypertension"
    return "general"


def chunk_pdf_by_sections(text: str, pdf_filename: str) -> list[dict]:
    """
    将 PDF 文本按 Recommendation 章节切片。
    ACE 指南的结构是 Recommendation 1, 2, 3...
    每个 Recommendation 作为一个 chunk，保留完整上下文。
    """
    chunks = []
    topic = detect_pdf_topic(pdf_filename, text)

    # 清理文本：去掉多余空行，但保留段落结构
    text = re.sub(r'\n{3,}', '\n\n', text)

    # 按 "Recommendation N" 分割
    # 匹配 "Recommendation 1" 或 "Recommendation 1\n\n内容"
    rec_pattern = r'(Recommendation\s+\d+)'
    parts = re.split(rec_pattern, text)

    # parts 结构: [intro, "Recommendation 1", content1, "Recommendation 2", content2, ...]

    # Chunk 0: 引言部分（Recommendation 1 之前的内容）
    if parts[0].strip():
        intro_text = parts[0].strip()
        # 限制 intro 长度，太长则截断
        if len(intro_text) > 2000:
            intro_text = intro_text[:2000]
        chunks.append({
            "text": intro_text,
            "metadata": {
                "chunk_type": "guideline_introduction",
                "topic": topic,
                "source": f"ACE_{pdf_filename}",
                "source_type": "ace_clinical_guidance",
                "section": "introduction",
            }
        })

    # 合并每个 Recommendation 标题 + 内容
    i = 1
    while i < len(parts) - 1:
        rec_title = parts[i].strip()
        rec_content = parts[i + 1].strip() if i + 1 < len(parts) else ""
        full_section = f"{rec_title}\n\n{rec_content}"

        # 如果 chunk 太长（>2000字符），再按段落分割
        if len(full_section) > 2000:
            sub_chunks = split_long_section(full_section, rec_title, topic, pdf_filename)
            chunks.extend(sub_chunks)
        else:
            chunks.append({
                "text": full_section,
                "metadata": {
                    "chunk_type": "guideline_recommendation",
                    "topic": topic,
                    "source": f"ACE_{pdf_filename}",
                    "source_type": "ace_clinical_guidance",
                    "section": rec_title,
                }
            })

        i += 2

    # 如果没有按 Recommendation 分割成功（可能 PDF 格式不同），按段落分割
    if len(chunks) <= 1:
        chunks = chunk_pdf_by_paragraphs(text, pdf_filename, topic)

    return chunks


def split_long_section(text: str, section_title: str, topic: str, pdf_filename: str) -> list[dict]:
    """将过长的章节按段落进一步分割，每个 chunk 约 800-1500 字符"""
    chunks = []
    paragraphs = text.split('\n\n')

    current_chunk = ""
    chunk_idx = 0
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(current_chunk) + len(para) > 1200 and current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    "chunk_type": "guideline_recommendation",
                    "topic": topic,
                    "source": f"ACE_{pdf_filename}",
                    "source_type": "ace_clinical_guidance",
                    "section": f"{section_title} (part {chunk_idx + 1})",
                }
            })
            current_chunk = para + "\n\n"
            chunk_idx += 1
        else:
            current_chunk += para + "\n\n"

    # 最后一段
    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {
                "chunk_type": "guideline_recommendation",
                "topic": topic,
                "source": f"ACE_{pdf_filename}",
                "source_type": "ace_clinical_guidance",
                "section": f"{section_title} (part {chunk_idx + 1})" if chunk_idx > 0 else section_title,
            }
        })

    return chunks


def chunk_pdf_by_paragraphs(text: str, pdf_filename: str, topic: str) -> list[dict]:
    """备用方案：当无法按 Recommendation 分割时，按段落分割"""
    chunks = []
    paragraphs = text.split('\n\n')

    current_chunk = ""
    chunk_idx = 0
    for para in paragraphs:
        para = para.strip()
        if not para or len(para) < 20:
            continue
        if len(current_chunk) + len(para) > 1200 and current_chunk:
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    "chunk_type": "guideline_content",
                    "topic": topic,
                    "source": f"ACE_{pdf_filename}",
                    "source_type": "ace_clinical_guidance",
                    "section": f"section_{chunk_idx}",
                }
            })
            current_chunk = para + "\n\n"
            chunk_idx += 1
        else:
            current_chunk += para + "\n\n"

    if current_chunk.strip():
        chunks.append({
            "text": current_chunk.strip(),
            "metadata": {
                "chunk_type": "guideline_content",
                "topic": topic,
                "source": f"ACE_{pdf_filename}",
                "source_type": "ace_clinical_guidance",
                "section": f"section_{chunk_idx}",
            }
        })

    return chunks


def load_all_pdf_chunks() -> list[dict]:
    """加载所有 ACE PDF 并返回 chunks"""
    all_chunks = []
    pdf_dir = ACE_PDF_DIR

    if not pdf_dir.exists():
        print(f"    警告: PDF 目录不存在: {pdf_dir}")
        return all_chunks

    for pdf_file in sorted(pdf_dir.glob("*.pdf")):
        print(f"    处理 PDF: {pdf_file.name}")
        text = extract_pdf_text(str(pdf_file))
        if not text or len(text) < 100:
            print(f"    跳过（内容为空或文件损坏）: {pdf_file.name}")
            continue

        chunks = chunk_pdf_by_sections(text, pdf_file.name)
        all_chunks.extend(chunks)
        print(f"      → {len(chunks)} chunks")

    return all_chunks


# ============================================================
# 主构建流程
# ============================================================

def build_vectorstore():
    """主函数：加载所有数据 → 切片 → Embedding → 存入 ChromaDB"""

    print("=" * 60)
    print("知识源向量化 — AI Innovation Challenge 2026")
    print("=" * 60)

    # 1. 加载 Embedding 模型
    print(f"\n[1/5] 加载 Embedding 模型: {EMBEDDING_MODEL}")
    print("    （首次运行会下载模型，约1-2GB，请耐心等待）")
    model = SentenceTransformer(EMBEDDING_MODEL)
    print(f"    ✓ 模型加载完成，向量维度: {model.get_sentence_embedding_dimension()}")

    # 2. 初始化 ChromaDB
    print(f"\n[2/5] 初始化 ChromaDB: {VECTORSTORE_DIR}")
    os.makedirs(VECTORSTORE_DIR, exist_ok=True)
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    # 3. 加载并处理所有数据
    print("\n[3/5] 加载并切片数据...")
    all_chunks = {}

    # --- 药物数据 ---
    drug_chunks = []
    drug_files = list((DATA_DIR / "drugs").glob("*.json"))
    for drug_file in drug_files:
        drugs = load_json(str(drug_file))
        for drug in drugs:
            drug_chunks.extend(chunk_drug_data(drug))
    all_chunks["drugs"] = drug_chunks
    print(f"    ✓ 药物知识: {len(drug_chunks)} chunks (from {len(drug_files)} files)")

    # --- 食物数据 ---
    food_chunks = []
    food_data = load_json(str(DATA_DIR / "food" / "sg_hawker_food.json"))
    for food in food_data:
        food_chunks.extend(chunk_food_data(food))
    # 饮品数据
    drinks_data = load_json(str(DATA_DIR / "food" / "sg_drinks_and_tips.json"))
    food_chunks.extend(chunk_drinks_data(drinks_data))
    all_chunks["food"] = food_chunks
    print(f"    ✓ 饮食知识: {len(food_chunks)} chunks")

    # --- 情绪支持 ---
    emotion_data = load_json(str(DATA_DIR / "emotion" / "emotion_support.json"))
    emotion_chunks = chunk_emotion_data(emotion_data)
    all_chunks["emotion"] = emotion_chunks
    print(f"    ✓ 情绪支持: {len(emotion_chunks)} chunks")

    # --- ACE 临床指南 PDF ---
    print("    加载 ACE 临床指南 PDF...")
    ace_chunks = load_all_pdf_chunks()
    if ace_chunks:
        all_chunks["ace_guidelines"] = ace_chunks
        print(f"    ✓ ACE 临床指南: {len(ace_chunks)} chunks")
    else:
        print("    ⚠ 未找到有效的 ACE PDF 文件")

    total_chunks = sum(len(v) for v in all_chunks.values())
    print(f"\n    总计: {total_chunks} chunks")

    # 4. Embedding & 存储
    print("\n[4/5] 生成 Embeddings 并存入 ChromaDB...")

    for data_type, chunks in all_chunks.items():
        collection_name = COLLECTIONS[data_type]

        # 删除旧 collection（如果存在）
        try:
            client.delete_collection(collection_name)
        except Exception:
            pass

        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"}  # 使用余弦相似度
        )

        # 批量处理（每批 50 个）
        batch_size = 50
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            metadatas = [c["metadata"] for c in batch]
            ids = [generate_doc_id(t) for t in texts]

            # 生成 embeddings
            embeddings = model.encode(texts, show_progress_bar=False).tolist()

            collection.add(
                documents=texts,
                embeddings=embeddings,
                metadatas=metadatas,
                ids=ids,
            )

        print(f"    ✓ {collection_name}: {len(chunks)} documents indexed")

    # 5. 验证
    print("\n[5/5] 验证向量数据库...")
    for collection_name in COLLECTIONS.values():
        col = client.get_collection(collection_name)
        count = col.count()
        print(f"    ✓ {collection_name}: {count} documents")

    print("\n" + "=" * 60)
    print("✅ 向量化完成！")
    print(f"   数据库位置: {VECTORSTORE_DIR}")
    print(f"   Embedding模型: {EMBEDDING_MODEL}")
    print(f"   总文档数: {total_chunks}")
    print()
    print("📋 给师湘淇(RAG Tool)的对接信息:")
    print(f"   ChromaDB 路径: {VECTORSTORE_DIR}")
    print(f"   Collection 名称: {list(COLLECTIONS.values())}")
    print(f"   Embedding 模型: {EMBEDDING_MODEL}")
    print(f"   向量维度: {model.get_sentence_embedding_dimension()}")
    print(f"   相似度: cosine")
    print("=" * 60)


# ============================================================
# 测试检索（可选）
# ============================================================

def test_search():
    """简单测试检索功能"""
    print("\n🔍 测试检索...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    client = chromadb.PersistentClient(path=str(VECTORSTORE_DIR))

    test_queries = [
        ("drug_knowledge", "二甲双胍什么时候吃？饭前还是饭后？"),
        ("drug_knowledge", "What are the side effects of Atorvastatin?"),
        ("food_knowledge", "我中午吃了海南鸡饭，对我的血糖有什么影响？"),
        ("food_knowledge", "Nasi Lemak healthy for hypertension?"),
        ("clinical_knowledge", "血糖多少算正常？"),
        ("clinical_knowledge", "高血压危险值是多少？需要去急诊吗？"),
        ("emotion_support", "我不想吃药了，吃了也没有用"),
        ("food_knowledge", "Kopi O Kosong 和 Teh Tarik 哪个更健康？"),
        ("ace_guidelines", "HbA1c target for elderly patients"),
        ("ace_guidelines", "SGLT2 inhibitor vs GLP-1 RA cardiorenal benefit"),
        ("ace_guidelines", "LDL-C target for diabetes patient"),
        ("ace_guidelines", "statin intensity classification"),
    ]

    for collection_name, query in test_queries:
        collection = client.get_collection(collection_name)
        query_embedding = model.encode([query]).tolist()

        results = collection.query(
            query_embeddings=query_embedding,
            n_results=2,
        )

        print(f"\n  查询: {query}")
        print(f"  Collection: {collection_name}")
        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            print(f"  [{i+1}] 相似度: {1-dist:.4f} | 类型: {meta.get('chunk_type', '')} | 来源: {meta.get('source', '')}")
            print(f"      {doc[:120]}...")
        print()


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--test":
        test_search()
    else:
        build_vectorstore()
        print("\n运行 python scripts/build_vectorstore.py --test 来测试检索效果")
