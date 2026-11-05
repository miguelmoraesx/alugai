import assert from "node:assert/strict"
import test from "node:test"
import { distanceKm, estimateTravel, rankNearbyPlaces, validateDestination } from "../lib/location.ts"

const property = { latitude: -3.0839, longitude: -59.9923 }

test("distanceKm returns zero for the same point", () => {
  assert.equal(distanceKm(property, property), 0)
})

test("distanceKm calculates a plausible Manaus urban distance", () => {
  const distance = distanceKm(property, { latitude: -3.1018136, longitude: -60.0141253 })
  assert.ok(distance > 2.5 && distance < 4)
})

test("estimateTravel exposes direct and estimated route distance", () => {
  const result = estimateTravel(property, { latitude: -3.1018136, longitude: -60.0141253 }, "driving")
  assert.ok(result.estimatedRouteKm > result.directDistanceKm)
  assert.ok(result.minutes >= 1)
})

test("validateDestination accepts the serviced region and rejects unsupported places", () => {
  assert.deepEqual(validateDestination({ ...property, city: "Manaus" }), { valid: true })
  assert.equal(validateDestination({ ...property, city: "São Paulo" }).valid, false)
  assert.equal(validateDestination({ latitude: -23.55, longitude: -46.63, city: "Manaus" }).valid, false)
})

test("rankNearbyPlaces is deterministic and boosts a preferred category", () => {
  const defaultRanking = rankNearbyPlaces(property, [], 4)
  const healthRanking = rankNearbyPlaces(property, ["health"], 4)
  assert.equal(defaultRanking.length, 4)
  assert.ok(defaultRanking.every((place, index) => index === 0 || defaultRanking[index - 1].score >= place.score))
  assert.equal(healthRanking[0].category, "health")
  assert.match(healthRanking[0].reason, /prioridade/)
})
