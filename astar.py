import sys, math
from heapq import heappush, heappop  # Heap for the priority queue
from collections import defaultdict

import numpy as np  # To compute sum[i] = num[i] + sum[i+1]
from fenwick import FenwickTree  # To add and remove matches

from utils import ceildiv, read_fasta_file, print_stats

h_dijkstra = lambda ij: 0  # Dijkstra's dummy heuristic


def build_seedh(A, B, k):
    """Builds the admissible seed heuristic for strings A and B with k-mers."""
    seeds = [A[i : i + k] for i in range(0, len(A) - k + 1, k)]  # O(n)
    kmers = {
        B[j : j + k] for j in range(len(B) - k + 1)
    }  # O(nk), O(n) with rolling hash (Rabin-Karp)
    is_seed_missing = [s not in kmers for s in seeds] + [False] * 2  # O(n)
    suffix_sum = np.cumsum(is_seed_missing[::-1])[::-1]  # O(n)
    return lambda ij, k=k: suffix_sum[ceildiv(ij[0], k)]  # O(1)


def build_seedh_for_pruning(A, B, k):
    S = [A[i : i + k] for i in range(0, len(A) - k + 1, k)]
    K = defaultdict(set)
    [K[B[j : j + k]].add(j) for j in range(len(B) - k + 1)]
    M = [K[s] for s in range(len(S))]
    misses = FenwickTree(len(S) + 2)
    misses.init([not js for js in M] + [0] * 2)

    return lambda ij, k=k, M=M, misses=misses: misses.range_sum(
        ceildiv(ij[0], k), len(misses)
    )


def next_states_with_cost(u, A, B):
    """Generates three states following curr (right, down, diagonal) with cost 0
    for match, 1 otherwise."""
    return [
        ((u[0] + 1, u[1]), 1),
        ((u[0], u[1] + 1), 1),
        ((u[0] + 1, u[1] + 1), A[u[0]] != B[u[1]]),
    ]


def align(A, B, h):
    """Standard A* on the grid A x B using a given heuristic h.

    :param A: string A
    :param B: string B
    :param h: heuristic function `h(ij) -> int`, where `ij` is a tuple of two integers
    :return: Result object with the cost to target, distance to target, and number of comparisons.
    """
    start = (0, 0)  # Start state
    target = (len(A), len(B))  # Target state
    Q = []  # Priority queue with candidate states
    heappush(Q, (0, start))  # Push start state with priority 0
    g = {start: 0}  # Cost of getting to each state
    A += "!"
    B += "!"  # Barrier to avoid index out of bounds
    comparisons = 0

    while Q:
        _, u = heappop(Q)  # Pop state u with lowest priority
        if u == target:
            return (
                g,  # costs dictionary
                g[(len(A) - 1, len(B) - 1)],  # distance from A to B
                comparisons,  # number of matrix cells evaluated
            )

        if u[0] > target[0] or u[1] > target[1]:
            continue  # Skip states after target

        if hasattr(h, "misses"):  # If the heuristic supports pruning
            if not u[0] % h.k:  # If expanding at the beginning of a seed
                s = u[0] // h.k
                if u[1] in h.M[s]:  # If the expanded state is a beginning of a match
                    h.M.remove(s, u[1])  # Remove match from M
                    assert len(h.M[s]) >= 0
                    # If no more matches for this seed, then increase the misses
                    if not h.M[s]:
                        assert not h.misses[s]
                        h.misses.add(s, +1)

        for v, edit_cost in next_states_with_cost(u, A, B):  # For all edges u->v
            new_cost_to_next = g[u] + edit_cost  # Try optimal path through u->v
            if v not in g or new_cost_to_next < g[v]:  # If new path is better
                g[v] = new_cost_to_next  # Update cost to v
                priority = new_cost_to_next + h(v)  # Compute priority
                heappush(Q, (priority, v))  # Push v with new priority
            comparisons += 1


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python astar.py <A.fa> <A.fa>")
    else:
        A, B = map(read_fasta_file, sys.argv[1:3])
        k = math.ceil(math.log(len(A), 4))
        h_seed = build_seedh(A, B, k)

        g_seed, distance_seed, comparisons_seed = align(A, B, h_seed)
        print_stats(A, B, k, g_seed)
