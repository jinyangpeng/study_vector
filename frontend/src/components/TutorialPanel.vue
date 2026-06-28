<script setup lang="ts">
// TutorialPanel：渲染 Markdown 教学文档
// 用法：<TutorialPanel slug="01-first-collection" />
// Markdown 文件位置：src/tutorials/milvus/{slug}.md
import { ref, watch, onMounted } from 'vue'
import MarkdownIt from 'markdown-it'
import hljs from 'highlight.js/lib/common'
import 'highlight.js/styles/atom-one-dark.css'

const props = defineProps<{
  slug: string // 教学文档名（不含 .md）
  category?: 'milvus' | string // 默认 milvus
}>()

const content = ref<string>('')
const error = ref<string>('')

const md: MarkdownIt = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true,
  highlight(str: string, lang: string): string {
    if (lang && hljs.getLanguage(lang)) {
      try {
        return `<pre class="hljs"><code>${
          hljs.highlight(str, { language: lang, ignoreIllegals: true }).value
        }</code></pre>`
      } catch {
        /* fall through */
      }
    }
    return `<pre class="hljs"><code>${md.utils.escapeHtml(str)}</code></pre>`
  },
})

async function load(slug: string) {
  content.value = ''
  error.value = ''
  try {
    // 用 ?raw 拿到纯文本（Vite 特性）
    const cat = props.category || 'milvus'
    const mod: any = await import(`@/tutorials/${cat}/${slug}.md?raw`)
    content.value = mod.default || ''
  } catch (e: any) {
    error.value = `教程未找到：${slug}.md（${e.message || e}）`
  }
}

onMounted(() => load(props.slug))
watch(
  () => props.slug,
  (s) => load(s),
)

const rendered = ref('')
watch(content, (v) => {
  rendered.value = v ? md.render(v) : ''
})
</script>

<template>
  <div class="tutorial-panel">
    <div class="panel-header">
      <span class="icon">📖</span>
      <span class="title">教学示例</span>
      <span class="slug">{{ slug }}.md</span>
    </div>
    <div v-if="error" class="error">{{ error }}</div>
    <div v-else-if="!content" class="loading">加载中…</div>
    <article v-else class="markdown-body" v-html="rendered" />
  </div>
</template>

<style scoped>
.tutorial-panel {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  background: #fff;
  margin-top: 16px;
  overflow: hidden;
}
.panel-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: linear-gradient(90deg, #f0f9ff, #fff);
  border-bottom: 1px solid #e4e7ed;
}
.panel-header .icon {
  font-size: 18px;
}
.panel-header .title {
  font-weight: 600;
  color: #303133;
}
.panel-header .slug {
  margin-left: auto;
  color: #909399;
  font-size: 12px;
  font-family: 'JetBrains Mono', Consolas, monospace;
}
.loading,
.error {
  padding: 24px;
  text-align: center;
  color: #909399;
}
.error {
  color: #f56c6c;
}
.markdown-body {
  padding: 20px 28px;
  max-width: 100%;
  overflow-x: auto;
  line-height: 1.7;
  color: #303133;
}
.markdown-body :deep(h1) {
  font-size: 22px;
  border-bottom: 2px solid #409eff;
  padding-bottom: 8px;
  margin-top: 0;
}
.markdown-body :deep(h2) {
  font-size: 18px;
  margin-top: 24px;
  padding-left: 10px;
  border-left: 4px solid #409eff;
}
.markdown-body :deep(h3) {
  font-size: 16px;
  color: #409eff;
  margin-top: 20px;
}
.markdown-body :deep(p) {
  margin: 10px 0;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 24px;
}
.markdown-body :deep(li) {
  margin: 4px 0;
}
.markdown-body :deep(code) {
  background: #f0f9ff;
  padding: 1px 6px;
  border-radius: 3px;
  font-family: 'JetBrains Mono', Consolas, monospace;
  font-size: 0.9em;
  color: #d63384;
}
.markdown-body :deep(pre) {
  margin: 12px 0;
  border-radius: 6px;
  overflow: auto;
}
.markdown-body :deep(pre code) {
  background: transparent;
  color: inherit;
  padding: 0;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 12px 0;
  width: 100%;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid #e4e7ed;
  padding: 6px 10px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f5f7fa;
  font-weight: 600;
}
.markdown-body :deep(blockquote) {
  margin: 12px 0;
  padding: 8px 14px;
  background: #fdf6ec;
  border-left: 4px solid #e6a23c;
  color: #5c4400;
}
.markdown-body :deep(a) {
  color: #409eff;
  text-decoration: none;
  border-bottom: 1px dashed #409eff;
}
</style>
