<template>
  <div class="profile-card">
    <h2>{{ title }}</h2>
    <p>{{ description }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from "vue";

const title = ref("Nexus-AI");
const description = ref("Onboarding técnico asistido por IA.");
</script>

<style scoped>
.profile-card {
  padding: 12px;
}
</style>
