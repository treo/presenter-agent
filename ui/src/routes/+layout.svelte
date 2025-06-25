<script lang="ts">
	import '$lib/app.css';
	import { onNavigate } from '$app/navigation';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import { Toaster } from '$lib/components/ui/sonner';

	let { children } = $props();

	// Define the routes in order
	const routes = [
		'/00-cover',
		'/01-paul-dubs',
		'/02-sci-fi-inspiration',
		//'/03-startreck-retro-computer',				
		'/04-what-is-ai-agent',
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

	// WebSocket connection and interval variables
	let ws: WebSocket | null = null;
	let routeInterval: number | null = null;

	// WebSocket connection function
	function connectWebSocket() {
		try {
			ws = new WebSocket('ws://127.0.0.1:9002/ws');
			
			ws.onopen = () => {
				console.log('WebSocket connected');
				// Send initial connection message with routes and current route
				sendMessage('connection');
			};
			
			ws.onclose = () => {
				console.log('WebSocket disconnected');
			};
			
			ws.onerror = (error) => {
				console.error('WebSocket error:', error);
			};
			
			ws.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data);
					console.log('WebSocket message received:', message);
					
					if (message.type === 'goto') {
						if (!message.route) {
							console.error('WebSocket goto message missing route data:', message);
							return;
						}
						
						// Validate that the route exists in the routes array
						if (!routes.includes(message.route)) {
							console.error('WebSocket goto message contains invalid route:', message.route);
							return;
						}
						
						console.log('Navigating to route:', message.route);
						goto(message.route);
					} else if (message.type === 'hint') {
						if (message.text) {
							console.log('Displaying hint message:', message.text);
							toast(message.text);
						} else {
							console.error('WebSocket hint message missing text data:', message);
						}
					}
				} catch (error) {
					console.error('Failed to parse WebSocket message:', error, 'Raw message:', event.data);
				}
			};
		} catch (error) {
			console.error('Failed to create WebSocket connection:', error);
		}
	}

	// Function to send messages with different types
	function sendMessage(type: 'connection' | 'route_change' | 'heartbeat') {
		if (ws && ws.readyState === WebSocket.OPEN) {
			const currentRoute = page.route.id || page.url.pathname;
			try {
				const message = {
					type,
					currentRoute,
					...(type === 'connection' && { routes })
				};
				ws.send(JSON.stringify(message));
			} catch (error) {
				console.error('Failed to send WebSocket message:', error);
			}
		}
	}

	// Legacy function for backward compatibility (now uses heartbeat type)
	function sendRouteId() {
		sendMessage('heartbeat');
	}

	// Reactive route change detection
	$effect(() => {
		// Watch for changes in the current route
		const currentRoute = page.route.id || page.url.pathname;
		
		// Send route change message when route changes (but not on initial load)
		if (ws && ws.readyState === WebSocket.OPEN) {
			sendMessage('route_change');
		}
	});

	onMount(() => {
		document.addEventListener('keydown', handleKeydown);
		
		// Initialize WebSocket connection
		connectWebSocket();
		
		// Set up interval to send route ID every 5 seconds as fallback
		routeInterval = setInterval(sendRouteId, 5000);

		return () => {
			document.removeEventListener('keydown', handleKeydown);
			
			// Clean up WebSocket connection
			if (ws) {
				ws.close();
				ws = null;
			}
			
			// Clear the interval
			if (routeInterval) {
				clearInterval(routeInterval);
				routeInterval = null;
			}
		};
	});
</script>

<svelte:head>
	<title>From Sci-Fi Dreams to Reality</title>
</svelte:head>

<div class="w-[100vw] h-[100vh] flex items-center justify-center">
	<div
		class="aspect-video w-full h-full mx-auto my-auto border p-8 relative overflow-hidden"
		style:view-transition-name="current-slide"
	>
		{@render children()}
	</div>
</div>

<Toaster />
