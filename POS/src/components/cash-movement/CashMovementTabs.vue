<template>
	<div class="flex flex-wrap gap-2">
		<button
			v-for="tab in tabs"
			:key="tab.key"
			type="button"
			@click="emit('select', tab.key)"
			:class="[
				'px-4 py-2 rounded-lg border text-sm font-semibold transition-colors',
				movementType === tab.key
					? tab.activeClass
					: 'bg-white border-gray-200 text-gray-600 hover:border-gray-300'
			]"
		>
			{{ __(tab.label) }}
		</button>
	</div>
</template>

<script setup>
const __ = window.__ || ((text) => text)

defineProps({
	tabs: {
		type: Array,
		default: () => [],
	},
	movementType: {
		type: String,
		default: "",
	},
})

const emit = defineEmits(["select"])
</script>
