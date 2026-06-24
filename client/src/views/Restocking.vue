<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>

      <!-- Empty state: no candidates at all -->
      <div v-if="candidates.length === 0" class="card">
        <p class="empty-message">{{ t('restocking.noCandidates') }}</p>
      </div>

      <template v-else>
        <!-- Budget slider card -->
        <div class="card">
          <div class="slider-label-row">
            <span class="slider-label">{{ t('restocking.budgetLabel') }}</span>
            <span class="slider-current-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
          </div>
          <div class="slider-container">
            <input
              type="range"
              v-model.number="budget"
              :min="0"
              :max="maxBudget"
              :step="sliderStep"
              class="budget-slider"
            />
          </div>
          <div class="slider-minmax-row">
            <span class="slider-bound">{{ currencySymbol }}0</span>
            <span class="slider-hint">{{ t('restocking.budgetHint') }}</span>
            <span class="slider-bound">{{ currencySymbol }}{{ maxBudget.toLocaleString() }}</span>
          </div>
        </div>

        <!-- Summary stats -->
        <div class="stats-grid">
          <div class="stat-card info">
            <div class="stat-label">{{ t('restocking.summary.allocated') }}</div>
            <div class="stat-value">{{ currencySymbol }}{{ allocatedTotal.toLocaleString() }}</div>
          </div>
          <div class="stat-card success">
            <div class="stat-label">{{ t('restocking.summary.remaining') }}</div>
            <div class="stat-value">{{ currencySymbol }}{{ budgetRemaining.toLocaleString() }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ t('restocking.summary.itemCount') }}</div>
            <div class="stat-value">{{ itemCount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">{{ t('restocking.summary.totalUnits') }}</div>
            <div class="stat-value">{{ totalUnits.toLocaleString() }}</div>
          </div>
        </div>

        <!-- Recommendations table card -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">{{ t('restocking.recommendations') }}</h3>
          </div>

          <div v-if="recommendations.length === 0" class="empty-message">
            {{ t('restocking.noRecommendations') }}
          </div>
          <div v-else class="table-container">
            <table class="table">
              <thead>
                <tr>
                  <th>{{ t('restocking.table.sku') }}</th>
                  <th>{{ t('restocking.table.itemName') }}</th>
                  <th>{{ t('restocking.table.trend') }}</th>
                  <th>{{ t('restocking.table.gap') }}</th>
                  <th>{{ t('restocking.table.recommendedQty') }}</th>
                  <th>{{ t('restocking.table.unitCost') }}</th>
                  <th>{{ t('restocking.table.lineTotal') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in recommendations" :key="item.item_sku">
                  <td><strong>{{ item.item_sku }}</strong></td>
                  <td>{{ translateProductName(item.item_name) }}</td>
                  <td>
                    <span :class="['badge', item.trend]">
                      {{ t(`trends.${item.trend}`) }}
                    </span>
                  </td>
                  <td>{{ item.gap }}</td>
                  <td>
                    {{ item.recommended_quantity }}
                    <span v-if="item.partial" class="partial-label">({{ t('restocking.partial') }})</span>
                  </td>
                  <td>{{ currencySymbol }}{{ item.unit_cost }}</td>
                  <td><strong>{{ currencySymbol }}{{ item.line_total.toLocaleString() }}</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Place order area -->
        <div class="place-order-area">
          <button
            class="place-order-btn"
            :disabled="submitting || recommendations.length === 0"
            @click="placeOrder"
          >
            {{ submitting ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>

          <div v-if="placedOrder" class="success-panel">
            <h3 class="success-title">{{ t('restocking.successTitle') }}</h3>
            <p>
              {{
                t('restocking.successMessage', {
                  orderNumber: placedOrder.order_number,
                  date: formatDate(placedOrder.expected_delivery),
                  days: placedOrder.lead_time_days
                })
              }}
            </p>
            <router-link to="/orders" class="success-link">{{ t('restocking.viewInOrders') }}</router-link>
          </div>
        </div>
      </template>

    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { t, currentLocale, currentCurrency, translateProductName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    // State
    const loading = ref(true)
    const error = ref(null)
    const candidates = ref([])
    const budget = ref(0)
    const submitting = ref(false)
    const placedOrder = ref(null)

    const loadCandidates = async () => {
      try {
        loading.value = true
        error.value = null
        const data = await api.getRestockCandidates()
        candidates.value = data

        // Initialize budget to 50% of total gap cost, rounded
        const total = data.reduce((sum, c) => sum + c.gap_cost, 0)
        budget.value = Math.round(total * 0.5)
      } catch (err) {
        error.value = 'Failed to load restock candidates: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Computed: total gap cost across all candidates
    const totalGapCost = computed(() => {
      return candidates.value.reduce((sum, c) => sum + c.gap_cost, 0)
    })

    // Computed: slider max = ceil of total gap cost
    const maxBudget = computed(() => {
      return Math.ceil(totalGapCost.value)
    })

    // Computed: slider step (roughly 1% of max, at least 1)
    const sliderStep = computed(() => {
      return Math.max(1, Math.round(maxBudget.value / 100))
    })

    // Computed: budget allocation — walk candidates sorted by gap desc,
    // greedily assign units within remaining budget; do NOT break early so
    // cheaper items that still fit are included.
    const recommendations = computed(() => {
      // Defensive re-sort by gap descending (candidates should already be sorted)
      const sorted = [...candidates.value].sort((a, b) => b.gap - a.gap)

      const result = []
      let remaining = budget.value

      for (const c of sorted) {
        if (c.unit_cost <= 0) continue // guard against zero/negative unit cost
        const take = Math.min(c.gap, Math.floor(remaining / c.unit_cost))
        if (take > 0) {
          result.push({
            ...c,
            recommended_quantity: take,
            line_total: +(take * c.unit_cost).toFixed(2),
            partial: take < c.gap
          })
          remaining -= take * c.unit_cost
        }
        // continue even if take === 0 — a later item with smaller gap_cost might still fit
      }

      return result
    })

    // Summary computed values
    const allocatedTotal = computed(() => {
      return recommendations.value.reduce((sum, r) => sum + r.line_total, 0)
    })

    const budgetRemaining = computed(() => {
      return Math.max(0, Math.round(budget.value - allocatedTotal.value))
    })

    const itemCount = computed(() => {
      return recommendations.value.length
    })

    const totalUnits = computed(() => {
      return recommendations.value.reduce((sum, r) => sum + r.recommended_quantity, 0)
    })

    const formatDate = (dateString) => {
      const date = new Date(dateString)
      if (isNaN(date.getTime())) return dateString
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const placeOrder = async () => {
      if (recommendations.value.length === 0 || submitting.value) return

      submitting.value = true
      error.value = null
      try {
        const orderData = {
          items: recommendations.value.map(r => ({
            sku: r.item_sku,
            name: r.item_name,
            quantity: r.recommended_quantity,
            unit_price: r.unit_cost
          }))
        }
        const result = await api.createOrder(orderData)
        placedOrder.value = result
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadCandidates)

    return {
      t,
      currencySymbol,
      loading,
      error,
      candidates,
      budget,
      submitting,
      placedOrder,
      totalGapCost,
      maxBudget,
      sliderStep,
      recommendations,
      allocatedTotal,
      budgetRemaining,
      itemCount,
      totalUnits,
      formatDate,
      placeOrder,
      translateProductName
    }
  }
}
</script>

<style scoped>
/* Budget slider card internals */
.slider-label-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 0.75rem;
}

.slider-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.slider-current-value {
  font-size: 2rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.slider-container {
  margin-bottom: 0.5rem;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  cursor: pointer;
  height: 6px;
}

.slider-minmax-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.slider-bound {
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 500;
}

.slider-hint {
  font-size: 0.813rem;
  color: #94a3b8;
}

/* Partial label */
.partial-label {
  font-size: 0.75rem;
  color: #94a3b8;
  margin-left: 0.25rem;
}

/* Empty state message */
.empty-message {
  color: #64748b;
  font-size: 0.938rem;
  padding: 1rem 0;
}

/* Place order area */
.place-order-area {
  margin-bottom: 1.25rem;
}

/* Primary action button */
.place-order-btn {
  display: inline-block;
  padding: 0.625rem 1.5rem;
  background: #2563eb;
  color: #ffffff;
  font-size: 0.938rem;
  font-weight: 600;
  border: none;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.2s ease;
  margin-bottom: 1rem;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #cbd5e1;
  color: #94a3b8;
  cursor: not-allowed;
}

/* Success panel */
.success-panel {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #065f46;
  padding: 1rem 1.25rem;
  border-radius: 8px;
  font-size: 0.938rem;
}

.success-title {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.375rem;
  color: #065f46;
}

.success-link {
  display: inline-block;
  margin-top: 0.625rem;
  color: #059669;
  font-weight: 600;
  text-decoration: underline;
}

.success-link:hover {
  color: #047857;
}
</style>
