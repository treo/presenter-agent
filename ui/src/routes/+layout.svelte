<script lang="ts">
	import '$lib/app.css';
	import { onNavigate } from '$app/navigation';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';

	let { children } = $props();

	// Define the routes in order
	const routes = [
		'/00-cover',
		'/02-sci-fi-inspiration',
		'/03-image-slide',
		'/04-paul-dubs',
		'/05-gpt3-revelation',
		'/06-early-days',
		'/07-frameworks-problem',
		'/08-xircuits-solution',
		'/09-babyagi',
		'/10-xai-agents',
		'/11-xircuits-limitations',
		'/12-something-better',
		'/13-customer-feedback-1',
		'/14-customer-feedback-2',
		'/15-can-we-do-better',
		'/16-xaibo-next-generation',
		'/17-dependency-injection',
		'/18-dependency-injection-benefits',
		'/19-radical-transparency-proxy',
		'/20-radical-transparency-explanation',
		'/21-modularity',
		'/22-live-demo',
		'/23-demo-screenshot-1',
		'/24-demo-screenshot-2',
		'/25-demo-screenshot-3',
		'/26-demo-screenshot-4',
		'/27-demo-screenshot-5',
		'/28-demo-screenshot-6',
		'/29-demo-screenshot-7',
		'/30-demo-screenshot-8',
		'/31-get-hands-dirty',
		'/32-try-xaibo-today',
		'/33-roadmap',
		'/34-questions'
	];

	onNavigate((navigation) => {
		if (!document.startViewTransition) return;

		return new Promise((resolve) => {
			document.startViewTransition(async () => {
				resolve();
				await navigation.complete;
			});
		});
	});

	// Handle keyboard navigation
	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'ArrowLeft' || event.key === 'ArrowRight') {
			const currentPath = page.route.id || page.url.pathname;
			const currentIndex = routes.indexOf(currentPath);

			if (currentIndex === -1) return;

			let nextIndex: number;
			if (event.key === 'ArrowLeft') {
				nextIndex = currentIndex > 0 ? currentIndex - 1 : routes.length - 1;
			} else {
				nextIndex = currentIndex < routes.length - 1 ? currentIndex + 1 : 0;
			}

			goto(routes[nextIndex]);
		}
	}

	onMount(() => {
		document.addEventListener('keydown', handleKeydown);

		return () => {
			document.removeEventListener('keydown', handleKeydown);
		};
	});
</script>

<div class="w-[100vw] h-[100vh] flex items-center justify-center">
	<div
		class="w-[1280px] h-[720px] mx-auto my-auto border p-8 relative"
		style:view-transition-name="current-slide"
	>
		{@render children()}
	</div>
</div>
