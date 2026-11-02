<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'

import { useAuthStore } from '@/stores/auth'
import { useCartStore } from '@/stores/cart'

const auth = useAuthStore()
const cart = useCartStore()
const router = useRouter()
const route = useRoute()

const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function doLogin(username: string, password: string) {
  loading.value = true
  try {
    const data = await auth.login(username, password)
    await cart.refresh()
    ElMessage.success(`欢迎回来，${data.user.nickname || data.user.username}`)
    const redirect = route.query.redirect
    router.replace(typeof redirect === 'string' && redirect ? redirect : '/')
  } finally {
    loading.value = false
  }
}

async function handleSubmit() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  await doLogin(form.username, form.password)
}

function quickLogin(username: string, password: string) {
  form.username = username
  form.password = password
  void doLogin(username, password)
}
</script>

<template>
  <div class="auth-page">
    <div class="auth-card">
      <h1 class="auth-card__title">登录</h1>
      <p class="auth-card__subtitle">Auto Test Demo 商城 · 登录后可加购、下单、支付</p>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        @submit.prevent="handleSubmit"
      >
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            autocomplete="current-password"
            @keyup.enter="handleSubmit"
          />
        </el-form-item>
        <el-button
          type="primary"
          style="width: 100%"
          :loading="loading"
          @click="handleSubmit"
        >
          登录
        </el-button>
      </el-form>

      <div class="auth-card__quick">
        <el-button size="small" style="flex: 1" @click="quickLogin('testuser', '123456')">
          一键登录 testuser
        </el-button>
        <el-button size="small" style="flex: 1" @click="quickLogin('admin', 'admin123')">
          一键登录 admin
        </el-button>
      </div>

      <div class="auth-card__footer">
        还没有账号？
        <router-link to="/register">立即注册</router-link>
      </div>
    </div>
  </div>
</template>
