from engine.entities import Entity, EntityType, EntityState
from .base import DataSource
import random
import time

class MockSource(DataSource):
    """Generates fake infrastructure data for development."""

    name = "mock"

    def is_available(self) -> bool:
        return True

    def fetch(self) -> list[Entity]:
        now = time.time()
        entities = []

        # Cluster
        cluster = Entity(
            id="cluster-prod",
            type=EntityType.CLUSTER,
            name="Production",
            state=EntityState.HEALTHY,
            source=self.name,
            labels={"env": "production"},
        )
        entities.append(cluster)

        # Nodes
        for i in range(3):
            node_id = f"node-{i+1}"
            node = Entity(
                id=node_id,
                type=EntityType.NODE,
                name=f"node-{i+1}.prod.internal",
                state=EntityState.RUNNING,
                parent="cluster-prod",
                source=self.name,
                metrics={"cpu": random.randint(10, 80), "mem": random.randint(20, 90)},
                labels={"zone": f"zone-{chr(65+i)}"},
            )
            cluster.children.append(node_id)
            entities.append(node)

            # Services per node
            for j in range(random.randint(2, 4)):
                svc_id = f"svc-{i}-{j}"
                state = random.choice([
                    EntityState.HEALTHY, EntityState.HEALTHY,
                    EntityState.HEALTHY, EntityState.WARNING,
                ])
                svc = Entity(
                    id=svc_id,
                    type=EntityType.SERVICE,
                    name=random.choice(["api-gateway", "auth-service", "worker", "cache", "db-proxy", "scheduler"]),
                    state=state,
                    parent=node_id,
                    source=self.name,
                    metrics={
                        "cpu": random.randint(5, 95),
                        "mem": random.randint(10, 85),
                        "req_per_sec": random.randint(0, 500),
                        "error_rate": round(random.uniform(0, 0.1) if state == EntityState.HEALTHY else random.uniform(0.05, 0.5), 3),
                    },
                    labels={"version": f"v{random.randint(1,3)}.{random.randint(0,9)}.{random.randint(0,9)}"},
                )
                node.children.append(svc_id)
                entities.append(svc)

                # Containers per service
                for k in range(random.randint(1, 3)):
                    container_id = f"ctr-{i}-{j}-{k}"
                    container = Entity(
                        id=container_id,
                        type=EntityType.CONTAINER,
                        name=f"{svc.name}-{k}",
                        state=random.choice([EntityState.RUNNING, EntityState.RUNNING, EntityState.STOPPED]),
                        parent=svc_id,
                        source=self.name,
                        metrics={"uptime_hrs": round(random.uniform(0.1, 720), 1)},
                    )
                    svc.children.append(container_id)
                    entities.append(container)

        return entities
