<script>
	import { ImageBlob } from '$lib/components';
</script>

<div class="slide">
	<h1 class="slide-title">Dependency Injection</h1>
	<div class="grid grid-cols-[2fr_1fr] flex-grow gap-6">
		<div class="flex flex-col">
			<div class="code-block mb-6">
				<p class="text-green-400 mb-2"># Instead of this:</p>
				<p>def __init__(self):</p>
				<p class="ml-4">self.database = SQLiteDatabase()</p>
			</div>
			<div class="code-block">
				<p class="text-green-400 mb-2"># You do this:</p>
				<p>def __init__(self, database: Database):</p>
				<p class="ml-4">self.database = database</p>
			</div>
			<div class="flex-grow"></div>
		</div>
		<div>
			<ImageBlob
				imageName="images-053.png"
				borderRadius="55% 45% 25% 75% / 35% 65% 70% 30%"
				bgPosition="bg-right"
			/>
		</div>
	</div>
</div>
