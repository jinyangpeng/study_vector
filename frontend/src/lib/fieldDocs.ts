// 字段说明元数据（教学用）
// 来源：contracts/openapi.yaml 的 description 字段
// 每个字段 = 鼠标悬停 ⓘ 时展示的提示文本

export interface FieldDoc {
  /** 字段显示名（中文） */
  label: string
  /** 字段描述（教学提示） */
  desc: string
  /** 示例值 */
  example?: string
  /** 字段类型提示（用于 UI 渲染） */
  hint?: 'enum' | 'number' | 'string' | 'json' | 'bool' | 'vector'
  /** 候选值（用于 select） */
  options?: Array<{ value: string; label: string; desc?: string }>
}

// ============ CollectionSchema ============
export const collectionSchemaDocs: Record<string, FieldDoc> = {
  name: {
    label: '集合名称',
    desc: '集合名（字母开头，后续字符：字母 / 数字 / 下划线，长度 1-255）。类比 MySQL 的表名。',
    example: 'demo_chunks',
    hint: 'string',
  },
  dimension: {
    label: '向量维度',
    desc: '向量维度。**一旦创建不可修改**。需与嵌入模型输出一致：\n- OpenAI text-embedding-3-small = 1536\n- OpenAI text-embedding-3-large = 3072\n- BGE-base / m3e-base = 768\n- BGE-small = 384',
    example: '1536',
    hint: 'number',
  },
  metric: {
    label: '距离度量',
    desc: '向量之间的"远近"如何计算。\n- **COSINE**（余弦）：只看方向不看模长，文本嵌入**最常用**\n- **L2**（欧氏距离）：两点直线距离；对模长敏感\n- **IP**（内积）：未归一化向量的对齐度\n- **HAMMING / JACCARD**：二值向量专用',
    example: 'COSINE',
    hint: 'enum',
    options: [
      { value: 'COSINE', label: 'COSINE（余弦）', desc: '文本 / 嵌入语义检索' },
      { value: 'L2', label: 'L2（欧氏）', desc: '图像 / 坐标 / 物理距离' },
      { value: 'IP', label: 'IP（内积）', desc: '归一化向量 / 推荐系统' },
      { value: 'HAMMING', label: 'HAMMING（汉明）', desc: 'BinaryVector 专用' },
      { value: 'JACCARD', label: 'JACCARD（杰卡德）', desc: 'BinaryVector 专用' },
    ],
  },
  vector_type: {
    label: '向量数据类型',
    desc: '选错类型 = 维度/度量/索引全错。\n- **FloatVector**（默认）：通用 4×D bytes\n- **BinaryVector**：二值 D/8 bytes，配 HAMMING/JACCARD；维度必须 8 的倍数\n- **Float16/BFloat16Vector**：半精度 2×D bytes\n- **SparseFloatVector**：稀疏，配 IP；用 hybrid_search 接口\n- **Int8Vector**：量化 D bytes，配 L2',
    example: 'FloatVector',
    hint: 'enum',
    options: [
      { value: 'FloatVector', label: 'FloatVector（默认）' },
      { value: 'BinaryVector', label: 'BinaryVector（二值）' },
      { value: 'Float16Vector', label: 'Float16Vector（半精度）' },
      { value: 'BFloat16Vector', label: 'BFloat16Vector' },
      { value: 'SparseFloatVector', label: 'SparseFloatVector（稀疏）' },
      { value: 'Int8Vector', label: 'Int8Vector（量化）' },
    ],
  },
  primary_field: {
    label: '主键字段名',
    desc: '主键字段名（V1 固定 VARCHAR）。一般保持 `id`。',
    example: 'id',
    hint: 'string',
  },
  vector_field: {
    label: '向量字段名',
    desc: '向量字段名。一般保持 `vector`。',
    example: 'vector',
    hint: 'string',
  },
  description: {
    label: '集合描述',
    desc: '人类可读的集合说明。',
    example: '存放用户问题向量的集合',
    hint: 'string',
  },
  index_type: {
    label: '默认索引类型',
    desc: '集合创建时自动建的索引。\n- **AUTOINDEX**（生产推荐）：Milvus 自适应\n- **HNSW**：高召回 / 内存允许\n- **FLAT**：暴力精确',
    example: 'AUTOINDEX',
    hint: 'enum',
    options: [
      { value: 'AUTOINDEX', label: 'AUTOINDEX（推荐）' },
      { value: 'HNSW', label: 'HNSW' },
      { value: 'IVF_FLAT', label: 'IVF_FLAT' },
      { value: 'IVF_SQ8', label: 'IVF_SQ8' },
      { value: 'IVF_PQ', label: 'IVF_PQ' },
      { value: 'FLAT', label: 'FLAT（精确）' },
      { value: 'ANNOY', label: 'ANNOY' },
      { value: 'DISKANN', label: 'DISKANN' },
    ],
  },
  consistency_level: {
    label: '一致性等级',
    desc: 'CAP 三角取舍：**Strong** 最准但最慢；**Eventually** 最快但可能读旧数据。\n- **Strong**：金融/订单\n- **Session**（默认）：通用\n- **Bounded**：推荐/容忍旧数据\n- **Eventually**：监控/聚合',
    example: 'Session',
    hint: 'enum',
    options: [
      { value: 'Strong', label: 'Strong（强一致）' },
      { value: 'Session', label: 'Session（默认）' },
      { value: 'Bounded', label: 'Bounded（有界）' },
      { value: 'Eventually', label: 'Eventually（最终）' },
    ],
  },
}

// ============ VectorRecord ============
export const vectorRecordDocs: Record<string, FieldDoc> = {
  id: {
    label: '主键',
    desc: '主键值。留空时后端自动生成 UUID。生产建议用业务 ID（如文档 hash）。',
    example: 'doc-001-chunk-007',
    hint: 'string',
  },
  vector: {
    label: '向量',
    desc: '向量数组，长度必须 = 集合的 dimension。**先归一化**再做 IP 检索（等价 COSINE）。',
    example: '[0.012, -0.034, 0.056, 0.078]',
    hint: 'vector',
  },
  payload: {
    label: '业务元数据',
    desc: 'JSON 对象。存业务可检索的字段（如 `category`、`lang`、`tag`）。检索时用 filter 过滤。',
    example: '{"category": "news", "lang": "zh"}',
    hint: 'json',
  },
}

// ============ SearchRequest ============
export const searchRequestDocs: Record<string, FieldDoc> = {
  vector: {
    label: '查询向量',
    desc: '与集合向量同维度的查询向量。',
    example: '[0.1, 0.2, 0.3, 0.4]',
    hint: 'vector',
  },
  top_k: {
    label: 'Top-K',
    desc: '返回最相似的 K 条。建议 5-100。值越大越慢。',
    example: '10',
    hint: 'number',
  },
  filter_expr: {
    label: '标量过滤',
    desc: '在向量检索之前先做标量过滤，可显著提速。\n- 简单等值：`{"category": "news"}`\n- 范围：`{"price": {"$gt": 100}}`\n- 复合：`{"$or": [{"a": 1}, {"b": 2}]}`',
    example: '{"category": "news"}',
    hint: 'json',
  },
  output_fields: {
    label: '输出字段',
    desc: '返回结果中要包含的 payload 字段；不写则只返回 id+score。',
    example: '["title", "url"]',
    hint: 'json',
  },
  partition_names: {
    label: '限定分区',
    desc: '只搜索指定分区。空 = 全部分区。',
    example: '["y2024"]',
    hint: 'json',
  },
}

// ============ CreateIndexRequest ============
export const createIndexDocs: Record<string, FieldDoc> = {
  field_name: {
    label: '字段名',
    desc: '要建索引的字段名。一般是向量字段 `vector`。',
    example: 'vector',
    hint: 'string',
  },
  index_type: {
    label: '索引类型',
    desc: '索引算法。\n- **AUTOINDEX**（生产推荐）\n- **HNSW**：M/efConstruction 决定图质量\n- **IVF_FLAT / SQ8 / PQ**：nlist 决定聚类数\n- **FLAT**：暴力精确（基准）',
    example: 'HNSW',
    hint: 'enum',
    options: [
      { value: 'AUTOINDEX', label: 'AUTOINDEX' },
      { value: 'HNSW', label: 'HNSW（高召回）' },
      { value: 'IVF_FLAT', label: 'IVF_FLAT' },
      { value: 'IVF_SQ8', label: 'IVF_SQ8（4×压缩）' },
      { value: 'IVF_PQ', label: 'IVF_PQ（极大压缩）' },
      { value: 'FLAT', label: 'FLAT（暴力精确）' },
      { value: 'ANNOY', label: 'ANNOY' },
      { value: 'DISKANN', label: 'DISKANN' },
    ],
  },
  metric_type: {
    label: '距离度量',
    desc: '索引使用的距离度量。**必须与集合度量一致**，否则查询会报错。',
    example: 'COSINE',
    hint: 'enum',
    options: [
      { value: 'COSINE', label: 'COSINE' },
      { value: 'L2', label: 'L2' },
      { value: 'IP', label: 'IP' },
      { value: 'HAMMING', label: 'HAMMING' },
      { value: 'JACCARD', label: 'JACCARD' },
    ],
  },
  params: {
    label: '索引参数',
    desc: '索引专属参数（JSON）。常用：\n- HNSW：`{"M": 16, "efConstruction": 64}`\n- IVF：`{"nlist": 1024}`\n- IVF_PQ：`{"nlist": 1024, "m": 8, "nbits": 8}`',
    example: '{"M": 16, "efConstruction": 64}',
    hint: 'json',
  },
}

// ============ HybridSearchRequest ============
export const hybridSearchDocs: Record<string, FieldDoc> = {
  dense: {
    label: '稠密向量',
    desc: '语义检索向量（embedding 模型输出）。',
    example: '[0.1, 0.2, 0.3, 0.4]',
    hint: 'vector',
  },
  dense_weight: {
    label: '稠密路权重',
    desc: 'RRF 合并时稠密路的权重。默认 1.0。',
    example: '1.0',
    hint: 'number',
  },
  sparse: {
    label: '稀疏向量',
    desc: '关键词检索向量（SPLADE/BM25）。格式 `{关键词: 权重}`。',
    example: '{"kw1": 1.0, "kw2": 0.5}',
    hint: 'json',
  },
  sparse_weight: {
    label: '稀疏路权重',
    desc: 'RRF 合并时稀疏路的权重。默认 1.0。',
    example: '1.0',
    hint: 'number',
  },
  rrf_k: {
    label: 'RRF k',
    desc: 'RRF 平滑项。越大各路贡献越平均。常用 60。',
    example: '60',
    hint: 'number',
  },
}

// ============ Partition / Alias ============
export const partitionDocs: Record<string, FieldDoc> = {
  name: {
    label: '分区名',
    desc: '分区名（字母开头 + 字母数字下划线）。`y2024` / `tenant_a` 之类。',
    example: 'y2024',
    hint: 'string',
  },
}

export const aliasDocs: Record<string, FieldDoc> = {
  alias: {
    label: '别名',
    desc: '集合的别名。可让业务代码访问稳定的"逻辑名"，底层切集合不影响业务。\n\n**零停机切换**：drop + create 是两步；真实 Milvus 提供 `alterAlias` 原子操作。',
    example: 'docs_latest',
    hint: 'string',
  },
}

// ============ Database / User ============
export const databaseDocs: Record<string, FieldDoc> = {
  name: {
    label: '数据库名',
    desc: '数据库名。Milvus 默认有 `default` 数据库；多租户场景可建独立 DB。',
    example: 'tenant_a',
    hint: 'string',
  },
}

export const userDocs: Record<string, FieldDoc> = {
  user_name: {
    label: '用户名',
    desc: '用户名（字母开头 + 字母数字下划线）。',
    example: 'reader_01',
    hint: 'string',
  },
  password: {
    label: '密码',
    desc: '用户密码。长度 1-256。',
    example: 'P@ssw0rd!',
    hint: 'string',
  },
}
