<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { createProduct, updateProduct } from '@/api/admin'
import { listCategories, listProducts } from '@/api/catalog'
import type {
  Category,
  Product,
  ProductStatus,
  ProductUpdateInput,
} from '@/api/types'
import {
  formatDateTime,
  formatMoney,
  PRODUCT_STATUS_TEXT,
} from '@/utils/format'

const categories = ref<Category[]>([])
const products = ref<Product[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const categoryId = ref<number | undefined>(undefined)
const status = ref<ProductStatus | undefined>(undefined)
const loading = ref(false)

const dialogOpen = ref(false)
const submitting = ref(false)
const editingId = ref<number | null>(null)
const formRef = ref<FormInstance>()

const form = reactive({
  name: '',
  description: '',
  category_id: undefined as number | undefined,
  price: '',
  stock: 0,
  status: 'ON_SALE' as ProductStatus,
})

const rules: FormRules = {
  name: [
    { required: true, message: '请输入商品名称', trigger: 'blur' },
    { max: 128, message: '不超过 128 个字符', trigger: 'blur' },
  ],
  category_id: [{ required: true, message: '请选择分类', trigger: 'change' }],
  price: [
    { required: true, message: '请输入价格', trigger: 'blur' },
    {
      pattern: /^\d{1,8}(\.\d{1,2})?$/,
      message: '最多两位小数的正数',
      trigger: 'blur',
    },
    {
      validator: (_rule, value: string, callback) => {
        if (!value || Number(value) <= 0) {
          callback(new Error('价格必须大于 0'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
  stock: [
    { required: true, message: '请输入库存', trigger: 'blur' },
    {
      validator: (_rule, value: number, callback) => {
        if (value === null || value === undefined || value < 0) {
          callback(new Error('库存不能为负数'))
          return
        }
        callback()
      },
      trigger: 'blur',
    },
  ],
}

async function loadCategories() {
  categories.value = await listCategories()
}

async function loadProducts() {
  loading.value = true
  try {
    const data = await listProducts({
      page: page.value,
      size: size.value,
      category_id: categoryId.value,
      keyword: keyword.value.trim() || undefined,
      status: status.value,
    })
    products.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  void loadProducts()
}

function handlePageChange(value: number) {
  page.value = value
  void loadProducts()
}

function categoryName(id: number): string {
  return categories.value.find((item) => item.id === id)?.name ?? `分类 ${id}`
}

function resetForm() {
  form.name = ''
  form.description = ''
  form.category_id = categories.value[0]?.id
  form.price = ''
  form.stock = 0
  form.status = 'ON_SALE'
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialogOpen.value = true
  formRef.value?.clearValidate()
}

function openEdit(row: Product) {
  editingId.value = row.id
  form.name = row.name
  form.description = row.description
  form.category_id = row.category_id
  form.price = String(row.price)
  form.stock = row.stock
  form.status = row.status
  dialogOpen.value = true
  formRef.value?.clearValidate()
}

async function submit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (editingId.value === null) {
      await createProduct({
        name: form.name.trim(),
        description: form.description.trim(),
        category_id: form.category_id as number,
        price: form.price,
        stock: form.stock,
        status: form.status,
      })
      ElMessage.success('商品已创建')
    } else {
      const payload: ProductUpdateInput = {
        name: form.name.trim(),
        description: form.description.trim(),
        category_id: form.category_id,
        price: form.price,
        stock: form.stock,
        status: form.status,
      }
      await updateProduct(editingId.value, payload)
      ElMessage.success('商品已更新')
    }
    dialogOpen.value = false
    await loadProducts()
  } finally {
    submitting.value = false
  }
}

async function toggleStatus(row: Product, value: boolean) {
  const nextStatus: ProductStatus = value ? 'ON_SALE' : 'OFF_SALE'
  try {
    await updateProduct(row.id, { status: nextStatus })
    row.status = nextStatus
    ElMessage.success(`已${PRODUCT_STATUS_TEXT[nextStatus]}：${row.name}`)
  } catch {
    await loadProducts()
  }
}

onMounted(() => {
  void loadCategories()
  void loadProducts()
})
</script>

<template>
  <div>
    <div class="toolbar">
      <el-input
        v-model="keyword"
        placeholder="商品名称"
        clearable
        style="width: 200px"
        @keyup.enter="search"
        @clear="search"
      />
      <el-select
        v-model="categoryId"
        placeholder="全部分类"
        clearable
        style="width: 150px"
        @change="search"
      >
        <el-option
          v-for="item in categories"
          :key="item.id"
          :label="item.name"
          :value="item.id"
        />
      </el-select>
      <el-select
        v-model="status"
        placeholder="全部状态"
        clearable
        style="width: 140px"
        @change="search"
      >
        <el-option label="在售" value="ON_SALE" />
        <el-option label="已下架" value="OFF_SALE" />
      </el-select>
      <el-button type="primary" @click="search">查询</el-button>
      <el-button type="success" @click="openCreate">新建商品</el-button>
      <span class="muted" style="margin-left: auto">共 {{ total }} 件</span>
    </div>

    <el-table v-loading="loading" :data="products" border row-key="id">
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="商品名称" min-width="180" />
      <el-table-column label="分类" width="110">
        <template #default="{ row }">{{ categoryName(row.category_id) }}</template>
      </el-table-column>
      <el-table-column label="价格" width="120">
        <template #default="{ row }">{{ formatMoney(row.price) }}</template>
      </el-table-column>
      <el-table-column prop="stock" label="库存" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.stock <= 0" type="warning" size="small">{{ row.stock }}</el-tag>
          <span v-else>{{ row.stock }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="120" align="center">
        <template #default="{ row }">
          <el-switch
            :model-value="row.status === 'ON_SALE'"
            active-text="在售"
            inactive-text="下架"
            inline-prompt
            @change="(value: string | number | boolean) => toggleStatus(row, Boolean(value))"
          />
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="180">
        <template #default="{ row }">{{ formatDateTime(row.created_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="100" align="center">
        <template #default="{ row }">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div class="pagination">
      <el-pagination
        :current-page="page"
        :page-size="size"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="handlePageChange"
      />
    </div>

    <el-dialog
      v-model="dialogOpen"
      :title="editingId === null ? '新建商品' : `编辑商品 #${editingId}`"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="90px">
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" maxlength="128" placeholder="请输入商品名称" />
        </el-form-item>
        <el-form-item label="分类" prop="category_id">
          <el-select v-model="form.category_id" placeholder="请选择分类" style="width: 100%">
            <el-option
              v-for="item in categories"
              :key="item.id"
              :label="item.name"
              :value="item.id"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="价格" prop="price">
          <el-input v-model="form.price" placeholder="例如：99.90">
            <template #prefix>¥</template>
          </el-input>
        </el-form-item>
        <el-form-item label="库存" prop="stock">
          <el-input-number v-model="form.stock" :min="0" :max="999999" style="width: 200px" />
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="ON_SALE">在售</el-radio>
            <el-radio value="OFF_SALE">下架</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="3"
            maxlength="2000"
            show-word-limit
            placeholder="选填"
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogOpen = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submit">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>
