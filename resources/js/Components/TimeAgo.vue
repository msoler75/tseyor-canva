<script setup>
import { computed } from 'vue';

const props = defineProps({
  date: {
    type: [String, Date],
    required: true,
  },
  prefix: {
    type: String,
    default: 'Editado',
  },
});

const timeAgo = computed(() => {
  let dateObj = props.date instanceof Date ? props.date : new Date(props.date);
  if (!dateObj || isNaN(dateObj.getTime())) return '';
  const now = new Date();
  const diff = now - dateObj;
  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);
  const months = Math.floor(days / 30);
  const years = Math.floor(days / 365);

  if (years > 0) {
    return `${props.prefix} hace ${years} año${years > 1 ? 's' : ''}`;
  } else if (months > 0) {
    return `${props.prefix} hace ${months} mes${months > 1 ? 'es' : ''}`;
  } else if (days > 0) {
    return `${props.prefix} hace ${days} día${days > 1 ? 's' : ''}`;
  } else if (hours > 0) {
    return `${props.prefix} hace ${hours} hora${hours > 1 ? 's' : ''}`;
  } else if (minutes > 0) {
    return `${props.prefix} hace ${minutes} minuto${minutes > 1 ? 's' : ''}`;
  } else {
    return `${props.prefix} hace unos segundos`;
  }
});
</script>

<template>
  <span>{{ timeAgo }}</span>
</template>
