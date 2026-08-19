# 预测智能体项目 - 文档索引

## 📚 文档总览

本项目包含以下核心文档，帮助理解和使用预测智能体系统：

---

## 📖 主要文档

### 1. **TECHNOLOGY_FRAMEWORK_SUMMARY.md** ⭐⭐⭐
**完整的技术框架总结**

- **长度**：~23,000 字，719 行
- **内容**：
  - 项目整体架构（三层目录结构）
  - 数据流转管道（Raw → Interim → Processed）
  - 核心模块架构（Shared、Agents、DataCollectors、Tools、Processors）
  - Agent 框架详解
  - 数据采集客户端（OpenAlex、GDELT、GitHub）
  - 配置管理系统
  - 实验组织结构
  - 基线实验示例（2026-08-14_simple_baseline）
  - 环境与依赖
  - 数据源与 API 详解
  - 工作流与最佳实践
  - 关键设计决策
  - 扩展方向
  - 快速参考和常见错误排查

**适合**：需要深入理解整个系统的人员

---

### 2. **ARCHITECTURE_DIAGRAM.md** ⭐⭐⭐
**可视化架构图和流程图**

- **长度**：~32,000 字，735 行
- **内容**：
  - 整体系统架构图
  - 数据流转管道（ASCII 图）
  - Shared 模块架构
  - Agent 框架结构
  - 数据采集客户端架构
  - 处理器架构
  - 实验组织结构
  - 基线实验流程（4 个阶段）
  - 时间序列切分示意
  - 配置驱动的参数流
  - API 缓存机制
  - 数据质量检查流程
  - 模块依赖关系
  - 错误处理与恢复
  - 扩展点
  - 关键路径和性能估计

**适合**：需要快速理解系统流程和架构的人员

---

### 3. **QUICK_REFERENCE.md** ⭐⭐
**快速参考卡**

- **长度**：~10,000 字，407 行
- **内容**：
  - 项目概览（表格形式）
  - 目录结构速查
  - 核心模块速查（表格）
  - 数据源速查（OpenAlex、GDELT、GitHub）
  - 配置文件速查
  - 常用命令
  - 常用代码片段
  - 数据流转速查
  - 文件命名约定
  - 环境变量配置
  - 常见错误排查
  - 关键路径
  - 修改前检查清单
  - 设计规则速记
  - 实验 README 必答问题
  - 有用的链接

**适合**：需要快速查找信息的人员（开发者、研究员）

---

## 📋 项目原始文档

### 4. **README.md**（项目根目录）
项目总体介绍、目录说明、推荐工作流、命名约定、快速入口

### 5. **AGENTS.md**（项目根目录）
工作协议、设计规则、项目组织、版本管理、数据完整性、验证规范、通信风格

### 6. **Attempt/README.md**
实验代码的组织结构、分类说明、单次尝试的最小结构、README 必答问题、环境说明

### 7. **Attempt/Shared/README.md**
共享模块说明

### 8. **Attempt/Baselines/README.md**
基线实验分类说明

### 9. **Attempt/Baselines/experiments/2026-08-14_simple_baseline/README.md**
具体的基线实验说明（目标、假设、设计、运行命令、结果、下一步）

### 10. **Data/README.md**
数据流转、数据分层、数据命名、最低记录要求

### 11. **Resources/README.md**
资源分类、建议命名、资料记录要求

---

## 🗂️ 文档关系图

```
DOCUMENTATION_INDEX.md (本文件)
│
├─ TECHNOLOGY_FRAMEWORK_SUMMARY.md ⭐⭐⭐
│  └─ 最完整的技术文档
│     ├─ 项目架构
│     ├─ 模块详解
│     ├─ API 文档
│     ├─ 工作流程
│     └─ 最佳实践
│
├─ ARCHITECTURE_DIAGRAM.md ⭐⭐⭐
│  └─ 可视化架构和流程
│     ├─ ASCII 图表
│     ├─ 数据流
│     ├─ 模块关系
│     └─ 错误处理
│
├─ QUICK_REFERENCE.md ⭐⭐
│  └─ 快速查找卡
│     ├─ 命令速查
│     ├─ 代码片段
│     ├─ 常见错误
│     └─ 配置参考
│
└─ 项目原始文档
   ├─ README.md (项目总览)
   ├─ AGENTS.md (工作协议)
   ├─ Attempt/README.md (实验组织)
   ├─ Data/README.md (数据规范)
   └─ Resources/README.md (资源规范)
```

---

## 🎯 快速导航

### 我想...

#### 了解项目整体架构
→ 阅读 **TECHNOLOGY_FRAMEWORK_SUMMARY.md** 的"一、项目整体架构"部分

#### 理解数据流转过程
→ 阅读 **ARCHITECTURE_DIAGRAM.md** 的"二、数据流转管道"部分

#### 快速查找 API 信息
→ 查看 **QUICK_REFERENCE.md** 的"数据源速查"部分

#### 学习如何运行实验
→ 查看 **QUICK_REFERENCE.md** 的"常用命令"部分

#### 理解 Agent 框架
→ 阅读 **TECHNOLOGY_FRAMEWORK_SUMMARY.md** 的"三、核心模块架构 → 3.1.1 Agent 框架"部分

#### 了解基线实验
→ 阅读 **TECHNOLOGY_FRAMEWORK_SUMMARY.md** 的"五、基线实验示例"部分

#### 排查常见错误
→ 查看 **QUICK_REFERENCE.md** 的"常见错误排查"部分

#### 修改代码前的准备
→ 查看 **QUICK_REFERENCE.md** 的"修改前检查清单"部分

#### 理解配置系统
→ 阅读 **TECHNOLOGY_FRAMEWORK_SUMMARY.md** 的"三、核心模块架构 → 3.1.4 配置管理"部分

#### 添加新的数据源
→ 阅读 **ARCHITECTURE_DIAGRAM.md** 的"十一、扩展点"部分

---

## 📊 文档统计

| 文档 | 字数 | 行数 | 类型 | 优先级 |
|------|------|------|------|--------|
| TECHNOLOGY_FRAMEWORK_SUMMARY.md | ~23,000 | 719 | 完整参考 | ⭐⭐⭐ |
| ARCHITECTURE_DIAGRAM.md | ~32,000 | 735 | 可视化 | ⭐⭐⭐ |
| QUICK_REFERENCE.md | ~10,000 | 407 | 快速查找 | ⭐⭐ |
| README.md | ~500 | 31 | 总览 | ⭐⭐ |
| AGENTS.md | ~2,000 | 74 | 规范 | ⭐⭐ |
| Attempt/README.md | ~1,000 | 44 | 指南 | ⭐ |

---

## 🔍 按主题查找

### 系统架构
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 一、项目整体架构
- ARCHITECTURE_DIAGRAM.md → 一、整体系统架构

### 数据管理
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 二、数据流转管道
- ARCHITECTURE_DIAGRAM.md → 二、数据流转管道
- Data/README.md

### 模块设计
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 三、核心模块架构
- ARCHITECTURE_DIAGRAM.md → 三、Shared 模块架构

### API 集成
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 七、数据源与 API
- QUICK_REFERENCE.md → 数据源速查

### 实验管理
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 四、实验组织结构
- ARCHITECTURE_DIAGRAM.md → 四、实验组织结构
- Attempt/README.md

### 工作流程
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 九、工作流与最佳实践
- AGENTS.md

### 代码示例
- QUICK_REFERENCE.md → 常用代码片段
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 十三、快速参考

### 错误排查
- QUICK_REFERENCE.md → 常见错误排查
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 十三、快速参考 → 13.3 常见错误排查

### 配置参考
- QUICK_REFERENCE.md → 配置文件速查
- TECHNOLOGY_FRAMEWORK_SUMMARY.md → 三、核心模块架构 → 3.1.4 配置管理

---

## 💡 使用建议

### 首次使用项目
1. 阅读 `README.md`（项目总览）
2. 阅读 `AGENTS.md`（工作协议）
3. 浏览 `ARCHITECTURE_DIAGRAM.md`（理解流程）
4. 保存 `QUICK_REFERENCE.md`（日常查找）

### 日常开发
1. 使用 `QUICK_REFERENCE.md` 快速查找命令和代码片段
2. 遇到问题时查看"常见错误排查"
3. 修改代码前检查"修改前检查清单"

### 深入学习
1. 阅读 `TECHNOLOGY_FRAMEWORK_SUMMARY.md` 的相关章节
2. 查看 `ARCHITECTURE_DIAGRAM.md` 的流程图
3. 阅读源代码注释和文档字符串

### 添加新功能
1. 查看 `ARCHITECTURE_DIAGRAM.md` 的"十一、扩展点"
2. 阅读相关模块的源代码
3. 参考现有实验的结构

---

## 📝 文档维护

### 更新频率
- **TECHNOLOGY_FRAMEWORK_SUMMARY.md**：架构改动时更新
- **ARCHITECTURE_DIAGRAM.md**：流程改动时更新
- **QUICK_REFERENCE.md**：命令或常见错误改动时更新
- **其他文档**：按需更新

### 贡献指南
1. 修改文档前，确保改动准确无误
2. 保持文档的一致性和完整性
3. 更新相关的交叉引用
4. 提交 Git commit 时说明文档改动

---

## 🔗 相关资源

### 项目文件
- 项目根目录：`F:\Predictive agents`
- 代码目录：`F:\Predictive agents\Attempt`
- 数据目录：`F:\Predictive agents\Data`
- 资源目录：`F:\Predictive agents\Resources`

### 配置文件
- `Attempt/configs/default.yaml`：项目级配置
- `Attempt/configs/topics.yaml`：主题定义
- `Attempt/configs/sources.yaml`：数据源配置

### 实验示例
- `Attempt/Baselines/experiments/2026-08-14_simple_baseline/`：基线实验
- `Attempt/_template/`：实验模板

---

## ❓ 常见问题

### Q: 我应该从哪个文档开始？
A: 如果是首次使用，从 `README.md` 开始，然后阅读 `ARCHITECTURE_DIAGRAM.md` 理解流程。

### Q: 如何快速找到某个命令？
A: 使用 `QUICK_REFERENCE.md` 的"常用命令"部分。

### Q: 如何理解数据流转？
A: 查看 `ARCHITECTURE_DIAGRAM.md` 的"二、数据流转管道"部分。

### Q: 如何添加新的数据源？
A: 查看 `ARCHITECTURE_DIAGRAM.md` 的"十一、扩展点"部分。

### Q: 遇到错误怎么办？
A: 查看 `QUICK_REFERENCE.md` 的"常见错误排查"部分。

---

## 📞 联系与支持

- **项目根目录**：`F:\Predictive agents`
- **文档位置**：项目根目录下的 `.md` 文件
- **问题报告**：查看 `AGENTS.md` 的"7. User Review and Stop Rule"部分

---

## 📅 文档版本

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-08-17 | 初始版本，包含三个主要文档 |

---

**最后更新**：2026-08-17  
**维护者**：Predictive Agents 研究团队  
**项目根目录**：`F:\Predictive agents`
