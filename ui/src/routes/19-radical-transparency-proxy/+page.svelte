<script>
	import { ImageBlob } from '$lib/components';
</script>

<div class="slide">
	<h1 class="slide-title">Radical Transparency: The Proxy</h1>
	<div class="grid grid-cols-[2fr_1fr] flex-grow gap-6">
		<div class="flex flex-col">
			<div class="flex items-center justify-center flex-grow">
				<div class="text-center">
					<div class="bg-primary text-primary-foreground p-4 rounded-lg mb-4">Module A</div>
					<div class="flex justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-up-down-icon lucide-arrow-up-down"><path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></svg>
					</div>
					<div class="bg-accent text-accent-foreground p-4 rounded-lg my-4">Proxy</div>
					<div class="flex justify-center">
						<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-up-down-icon lucide-arrow-up-down"><path d="m21 16-4 4-4-4"/><path d="M17 20V4"/><path d="m3 8 4-4 4 4"/><path d="M7 4v16"/></svg>
					</div>
					<div class="bg-primary text-primary-foreground p-4 rounded-lg mt-4">Module B</div>
				</div>
				<div class="ml-8 flex gap-8 items-center">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-right-icon lucide-arrow-right"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
					<div class="bg-secondary text-secondary-foreground p-4 rounded-lg">
						Event<br />Listeners
					</div>
				</div>
			</div>
		</div>
		<div>
			<ImageBlob
				imageName="images-056.png"
				borderRadius="70% 30% 35% 65% / 45% 55% 80% 20%"
				bgPosition="bg-center"
			/>
		</div>
	</div>
</div>

<style lang="postcss">
	svg {
		height: 5vh;
		width: 5vh;
	}
</style>