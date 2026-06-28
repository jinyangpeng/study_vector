<script setup lang="ts">
// ParamHelp 组件：ⓘ 鼠标悬停显示字段说明（教学用）
// 用法：<ParamHelp field="CollectionSchema.name" />
// 或：   <ParamHelp :doc="myDoc" />

import { computed } from 'vue'

interface Option {
  value: string
  label: string
  desc?: string
}

interface FieldDoc {
  label: string
  desc: string
  example?: string
  hint?: 'enum' | 'number' | 'string' | 'json' | 'bool' | 'vector'
  options?: Option[]
}

const props = defineProps<{
  /** 直接传 FieldDoc 对象 */
  doc?: FieldDoc
}>()

const tooltip = computed(() => {
  if (!props.doc) return ''
  let text = `【${props.doc.label}】\n${props.doc.desc}`
  if (props.doc.example) text += `\n\n示例：${props.doc.example}`
  if (props.doc.options?.length) {
    text += '\n\n可选值：\n'
    for (const opt of props.doc.options) {
      text += `  • ${opt.value}`
      if (opt.desc) text += ` — ${opt.desc}`
      text += '\n'
    }
  }
  return text
})
</script>

<template>
  <el-tooltip
    v-if="doc"
    :content="tooltip"
    placement="top"
    :show-after="120"
    raw-content
    popper-class="param-help-popper"
  >
    <span class="param-help">ⓘ</span>
  </el-tooltip>
</template>

<style scoped>
.param-help {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ecf5ff;
  color: #409eff;
  font-size: 12px;
  cursor: help;
  margin-left: 4px;
  user-select: none;
  transition: background 0.2s;
}
.param-help:hover {
  background: #409eff;
  color: #fff;
}
</style>

<style>
.param-help-popper {
  max-width: 380px !important;
  white-space: pre-wrap !important;
  line-height: 1.5 !important;
  font-size: 13px !important;
}
</style>
