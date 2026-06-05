<script lang="ts">
  export interface PlaceholderSection {
    title: string;
    detail: string;
  }

  let {
    title,
    subtitle,
    sections,
  }: {
    title: string;
    subtitle: string;
    sections: PlaceholderSection[];
  } = $props();
</script>

<section class="page-placeholder-shell" aria-label={`${title} placeholder`}>
  <div class="placeholder-hero">
    <span class="placeholder-kicker">Coming next</span>
    <h2>{title}</h2>
    <p>{subtitle}</p>
  </div>

  <div class="placeholder-grid">
    {#each sections as section}
      <article class="placeholder-section-card">
        <span class="placeholder-section-rule"></span>
        <h3>{section.title}</h3>
        <p>{section.detail}</p>
      </article>
    {/each}
  </div>
</section>
