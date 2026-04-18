<template>
    <component :is="popupCard ? 'div' : Link" :href="route('usuario', { id: user.slug || user.id })"
        :title="user.name || user.nombre || user.slug" class="inline-block font-bold cursor-pointer"
        :class="props.class" @click="onClick">
        <template v-slot:default>
            <span v-if="!$slots.default">{{ name }}</span>
            <slot />
        </template>
    </component>
    <Modal :show="showCard" @close="showCard = false" maxWidth="sm">
        <div class="flex flex-col gap-2 p-5 items-center">
            <Avatar :user="user" :link="false" image-class="w-64 h-64" text-class="text-5xl"  />
            <h3>{{ name }}</h3>
            <div class="prose">
                <blockquote v-if="user.frase">
                    <p>{{ user.frase }}</p>
                </blockquote>
            </div>
            <div class="flex justify-between sm:justify-end gap-3">
                <Link class="btn" :href="route('usuario', { id: user.slug || user.id })">Ver Perfil del Usuario</Link>
                <button class="btn" @click="showCard = false">Cerrar</button>
            </div>
        </div>
    </Modal>
</template>

<script setup>
import { Link } from '@inertiajs/vue3'

const props = defineProps({
    user: { type: Object, required: true },
    popupCard: { type: Boolean, default: true },
    class: {type: String}
})

const name = computed(() => props.user.name || props.user.nombre)

const showCard = ref(false)

function onClick() {
    if (props.popupCard)
        showCard.value = true
}
</script>
