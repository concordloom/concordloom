(function exposeConcordData() {
  "use strict";

  const CATALOG_PATH = "/framework/concordloom/catalog.json";
  const COPY_PATH = "/site/data/atlas.json";
  const FIRST_REVISION = 5;

  async function fetchJson(path) {
    const response = await fetch(path, { cache: "no-store" });
    if (!response.ok) {
      throw new Error(`${path}: HTTP ${response.status}`);
    }
    return response.json();
  }

  function rootPath(path) {
    return path.startsWith("/") ? path : `/${path}`;
  }

  async function discoverSources() {
    const catalog = await fetchJson(CATALOG_PATH);
    const candidates = catalog.entries
      .map((entry) => {
        const match = entry.binding_id.match(/^concordloom-self-binding-v(\d+)$/);
        return match ? { entry, revision: Number(match[1]) } : null;
      })
      .filter((candidate) => candidate?.revision >= FIRST_REVISION)
      .sort((left, right) => left.revision - right.revision);

    const results = await Promise.allSettled(
      candidates.map(async ({ entry, revision }) => {
        const binding = await fetchJson(rootPath(entry.path));
        const registryArtifact = binding.artifacts.find(
          (artifact) => artifact.role === "cycle_registry",
        );
        if (!registryArtifact) {
          throw new Error(`${entry.path}: cycle_registry artifact is missing`);
        }
        return {
          id: `v${revision}`,
          label: String(revision),
          registryPath: rootPath(registryArtifact.path),
          latest: entry.binding_digest === catalog.active_binding_digest,
        };
      }),
    );

    const sources = results
      .filter((result) => result.status === "fulfilled")
      .map((result) => result.value);
    const missingBindings = results.length - sources.length;
    if (!sources.length || !sources.some((source) => source.latest)) {
      throw new Error("The active Concord Loom binding is unavailable");
    }
    return { sources, missingBindings };
  }

  function normalizeRegistry(source, registry, copyById) {
    const loops = new Map();
    registry.loops.forEach((loop) => {
      const localized = copyById.get(loop.id);
      loops.set(loop.id, {
        id: loop.id,
        label: localized?.label || loop.label || loop.id,
        purpose: localized?.purpose || loop.purpose || "Описание пока не задано.",
        children: [],
        parentIds: [],
      });
    });

    registry.containment_graph.edges.forEach((edge) => {
      const parent = loops.get(edge.parent_loop_id);
      const child = loops.get(edge.child_loop_id);
      if (!parent || !child) {
        return;
      }
      if (!parent.children.includes(child.id)) {
        parent.children.push(child.id);
      }
      if (!child.parentIds.includes(parent.id)) {
        child.parentIds.push(parent.id);
      }
    });

    loops.forEach((loop) => {
      loop.children.sort((left, right) => left.localeCompare(right));
      loop.parentIds.sort((left, right) => left.localeCompare(right));
    });

    const roots = registry.containment_graph.roots
      .filter((id) => loops.has(id))
      .sort((left, right) => left.localeCompare(right));
    if (!roots.length) {
      throw new Error(`${source.registryPath}: containment roots are missing`);
    }

    let rootId = roots[0];
    if (roots.length > 1) {
      rootId = "__atlas-root__";
      loops.set(rootId, {
        id: rootId,
        label: "Вся система",
        purpose: "Общий вход в независимые корневые циклы.",
        children: roots,
        parentIds: [],
        synthetic: true,
      });
    }

    return {
      id: source.id,
      label: source.label,
      latest: source.latest,
      loopCount: registry.loops.length,
      rootId,
      loops,
    };
  }

  async function load() {
    const [{ sources, missingBindings }, copyResult] = await Promise.all([
      discoverSources(),
      fetchJson(COPY_PATH).catch(() => ({ loops: [] })),
    ]);
    const copyById = new Map(
      copyResult.loops.map((loop) => [loop.id, loop.copy.ru]),
    );
    const registryResults = await Promise.allSettled(
      sources.map(async (source) => ({
        source,
        registry: await fetchJson(source.registryPath),
      })),
    );
    const available = registryResults
      .filter((result) => result.status === "fulfilled")
      .map((result) => result.value);
    const activeSource = sources.find((source) => source.latest);
    if (!available.some(({ source }) => source.id === activeSource.id)) {
      throw new Error("The active cycle registry is unavailable");
    }

    const models = new Map(
      available.map(({ source, registry }) => [
        source.id,
        normalizeRegistry(source, registry, copyById),
      ]),
    );
    return {
      sources: available.map(({ source }) => source),
      models,
      warnings: {
        missingArchives:
          missingBindings + (registryResults.length - available.length),
        missingCopy: copyById.size === 0,
      },
    };
  }

  window.ConcordData = { load };
})();
