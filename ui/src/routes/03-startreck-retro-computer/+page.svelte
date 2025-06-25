<script lang="ts">
  import Youtube from "svelte-youtube-embed";
</script>

<div class="image-slide -m-8 overflow-hidden inset-0 absolute" style="background-image: url('/images-010.png');">
    <Youtube id="hShY6xZWVGE" animations={false}>
        {#snippet thumbnail()}
    <img
      alt="Star Trek Computer Scene"
      src="/images-010.png"
      style="width: 100%; height: 100%; object-fit: contain; object-position: center;"
    />
  {/snippet}
    </Youtube>
</div>
