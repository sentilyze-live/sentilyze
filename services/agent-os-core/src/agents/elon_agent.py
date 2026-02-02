"""ELON Agent - Sentilyze Growth Architect & Experimentation Engine."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog

from src.agents.base import BaseAgent
from src.config import settings

logger = structlog.get_logger(__name__)


class ElonAgent(BaseAgent):
    """
    ELON - Sentilyze Growth Architect
    
    Metodoloji: Sean Ellis (Growth Hacking) + Data-Driven Experimentation
    
    Görev: Sentilyze MRR Growth'u yüksek hızlı, veriye dayalı deneylerle artırmak.
    ICE skorlama sistemi kullanır. SCOUT'tan gelen fırsatları growth experiment'lere dönüştürür.
    """

    def __init__(self):
        """Initialize ELON agent."""
        super().__init__(
            agent_type="elon",
            name="ELON (Growth Architect)",
            description="Sentilyze Growth Orchestrator & Experimentation Engine",
        )

        self.capabilities = [
            "ICE Experiment Scoring",
            "North Star Metric Tracking (MRR)",
            "Growth Loop Optimization",
            "A/B Test Design",
            "Conversion Funnel Analysis",
            "Agent Coordination",
        ]

        self.system_prompt = """You are ELON, Sentilyze's growth architect.

Your mission: Drive MRR growth through high-velocity experimentation.

NORTH STAR METRIC: Monthly Recurring Revenue (MRR)
SECONDARY METRICS:
- Signup Conversion Rate
- User Activation Rate (Day 7)
- Retention Rate (Day 30)
- Referral Rate

ICE SCORING FRAMEWORK:
- Impact (1-10): Potential MRR effect
- Confidence (1-10): Data/evidence level
- Ease (1-10): Implementation difficulty
- Total = (Impact × 4) + (Confidence × 3) + (Ease × 3)

GROWTH LOOPS TO OPTIMIZE:
1. Content Loop: SETH's SEO → Organic Traffic → Signups → Activation
2. Community Loop: ZARA's Engagement → Trust → Signups → Retention
3. Data Loop: SCOUT's Intel → Timely Content → Viral Traffic → Signups

EXPERIMENT PRINCIPLES:
1. Always have clear hypothesis
2. Define success metrics upfront
3. Run for minimum 1 week
4. Document everything (success or failure)
5. Share learnings with all agents

OUTPUT: Experiment proposals with ICE scores, implementation plans, and agent coordination requests"""

        self.version = "2.0.0"
        
        # ICE score thresholds
        self.min_ice_score = 24  # Minimum to propose
        self.high_ice_threshold = 32  # High priority threshold
        
        # Growth targets
        self.target_metrics = {
            "conversion_rate": 0.05,  # 5%
            "activation_rate": 0.30,  # 30%
            "retention_rate": 0.50,  # 50%
            "referral_rate": 0.10,  # 10%
        }

    async def _execute(self, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute ELON growth experimentation workflow.

        Args:
            context: Optional context with SCOUT directives or metrics

        Returns:
            Proposed experiments and growth insights
        """
        results = {
            "experiments_proposed": [],
            "experiments_running": [],
            "metrics_snapshot": {},
            "growth_insights": [],
            "agent_requests": {},
            "timestamp": datetime.utcnow().isoformat(),
        }

        # 1. Gather current metrics
        logger.info("elon.gathering_metrics")
        metrics = await self._gather_comprehensive_metrics()
        results["metrics_snapshot"] = metrics

        # 2. Check for SCOUT directives
        logger.info("elon.checking_scout_directives")
        scout_directives = context.get("scout_directives", []) if context else []
        scout_opportunities = await self._process_scout_directives(scout_directives)

        # 3. Analyze metric gaps
        logger.info("elon.analyzing_metric_gaps")
        metric_gaps = self._identify_metric_gaps(metrics)

        # 4. Generate experiment ideas from gaps + opportunities
        logger.info("elon.generating_experiments")
        experiment_sources = metric_gaps + scout_opportunities
        
        for source in experiment_sources:
            experiment = await self._design_experiment(source, metrics)
            
            if experiment and experiment["ice_scores"]["total"] >= self.min_ice_score:
                results["experiments_proposed"].append(experiment)

        # 5. Prioritize and filter experiments
        results["experiments_proposed"] = self._prioritize_experiments(
            results["experiments_proposed"]
        )

        # 6. Save and notify
        for experiment in results["experiments_proposed"][:5]:  # Top 5
            await self._publish_experiment(experiment)

        # 7. Generate growth insights
        results["growth_insights"] = await self._generate_growth_insights(
            metrics, results["experiments_proposed"]
        )

        # 8. Generate agent coordination requests
        results["agent_requests"] = await self._generate_agent_requests(
            metrics, results["experiments_proposed"]
        )

        # 9. Publish requests to other agents
        for agent, requests in results["agent_requests"].items():
            if requests:
                await self.pubsub.publish_agent_request(
                    target_agent=agent,
                    requests=requests,
                    source_agent="ELON",
                )

        logger.info(
            "elon.growth_analysis_complete",
            experiments=len(results["experiments_proposed"]),
            gaps_found=len(metric_gaps),
            insights=len(results["growth_insights"]),
        )

        return results

    async def _gather_comprehensive_metrics(self) -> Dict[str, Any]:
        """Gather comprehensive growth metrics.

        Returns:
            Current metrics snapshot
        """
        metrics = {
            "timestamp": datetime.utcnow().isoformat(),
            "mrr": {},
            "funnel": {},
            "engagement": {},
        }

        try:
            # Get user analytics
            analytics_30d = await self.bigquery.get_user_analytics(days=30)
            analytics_7d = await self.bigquery.get_user_analytics(days=7)
            
            # MRR metrics
            total_signups_30d = analytics_30d.get("total_signups", 0)
            total_activations_30d = analytics_30d.get("total_activations", 0)
            
            metrics["mrr"]["estimated_mrr"] = total_activations_30d * 29  # $29 avg
            metrics["mrr"]["total_signups_30d"] = total_signups_30d
            metrics["mrr"]["signup_growth_mom"] = self._calculate_growth_rate(
                analytics_30d.get("total_signups", 0),
                analytics_30d.get("prev_month_signups", total_signups_30d)
            )

            # Funnel metrics
            if total_signups_30d > 0:
                metrics["funnel"]["activation_rate"] = total_activations_30d / total_signups_30d
            else:
                metrics["funnel"]["activation_rate"] = 0
            
            metrics["funnel"]["conversion_rate"] = analytics_30d.get("conversion_rate", 0)
            
            # Calculate retention (placeholder)
            metrics["funnel"]["retention_rate"] = analytics_30d.get("retention_rate", 0.45)
            
            # Engagement metrics
            sentiment_volume = await self.bigquery.get_sentiment_data(hours=168)
            metrics["engagement"]["sentiment_volume_7d"] = len(sentiment_volume)
            metrics["engagement"]["prediction_accuracy"] = analytics_30d.get("prediction_accuracy", 0)

            # Identify biggest gap
            gaps = self._identify_metric_gaps(metrics)
            metrics["priority_gap"] = gaps[0] if gaps else None

        except Exception as e:
            logger.error("elon.metrics_error", error=str(e))
            metrics["error"] = str(e)

        return metrics

    def _calculate_growth_rate(self, current: float, previous: float) -> float:
        """Calculate growth rate."""
        if previous > 0:
            return (current - previous) / previous
        return 0.0

    def _identify_metric_gaps(self, metrics: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify gaps in metrics vs targets.

        Args:
            metrics: Current metrics

        Returns:
            List of gaps
        """
        gaps = []
        
        funnel = metrics.get("funnel", {})
        
        # Check each target metric
        for metric_name, target in self.target_metrics.items():
            current = funnel.get(metric_name, 0)
            gap = target - current
            
            if gap > 0:
                opportunity_size = self._estimate_opportunity_size(metric_name, gap)
                
                gaps.append({
                    "type": "metric_gap",
                    "metric": metric_name,
                    "current": current,
                    "target": target,
                    "gap": gap,
                    "gap_percentage": (gap / target) * 100,
                    "priority": "High" if gap > (target * 0.3) else "Medium",
                    "opportunity_size": opportunity_size,
                    "source": "metrics_analysis",
                })
        
        # Sort by opportunity size
        gaps.sort(key=lambda x: x["opportunity_size"], reverse=True)
        
        return gaps

    def _estimate_opportunity_size(self, metric: str, gap: float) -> float:
        """Estimate opportunity size in potential MRR."""
        # Assume 1000 current MRR for calculation
        base_mrr = 1000
        
        multipliers = {
            "conversion_rate": base_mrr * 2,  # Double conversion = big impact
            "activation_rate": base_mrr * 1.5,
            "retention_rate": base_mrr * 3,  # Retention is huge
            "referral_rate": base_mrr * 1.2,
        }
        
        return gap * multipliers.get(metric, base_mrr)

    async def _process_scout_directives(
        self, 
        directives: List[Dict]
    ) -> List[Dict[str, Any]]:
        """Process SCOUT directives into experiment opportunities.

        Args:
            directives: SCOUT directives

        Returns:
            Experiment opportunities
        """
        opportunities = []

        for directive in directives:
            action = directive.get("action")
            
            if action == "design_experiment":
                opportunities.append({
                    "type": "scout_opportunity",
                    "subtype": directive.get("type"),
                    "metric": directive.get("target_metric"),
                    "potential_lift": directive.get("potential_lift"),
                    "priority": directive.get("priority", "Medium"),
                    "rationale": directive.get("rationale", ""),
                    "source": "SCOUT",
                })

        return opportunities

    async def _design_experiment(
        self,
        source: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Design an experiment based on source.

        Args:
            source: Opportunity source
            metrics: Current metrics

        Returns:
            Experiment design
        """
        try:
            if source["type"] == "metric_gap":
                return await self._design_gap_experiment(source, metrics)
            elif source["type"] == "scout_opportunity":
                return await self._design_scout_experiment(source, metrics)
            else:
                return None
        except Exception as e:
            logger.error("elon.experiment_design_error", source=source, error=str(e))
            return None

    async def _design_gap_experiment(
        self,
        gap: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Design experiment for a metric gap.

        Args:
            gap: Metric gap
            metrics: Current metrics

        Returns:
            Experiment design
        """
        metric = gap["metric"]
        current = gap["current"]
        target = gap["target"]
        
        # Generate experiment based on metric type
        experiments = {
            "conversion_rate": {
                "name": f"{metric.replace('_', ' ').title()} Landing Page Optimization",
                "hypothesis": f"Improving landing page clarity will increase {metric} from {current:.1%} to {target:.1%}",
                "variants": ["control", "benefit_focused", "social_proof_heavy"],
                "duration_days": 14,
                "ice": {"impact": 8, "confidence": 7, "ease": 8},
            },
            "activation_rate": {
                "name": f"{metric.replace('_', ' ').title()} Onboarding Flow Redesign",
                "hypothesis": f"Simplifying onboarding will increase {metric} from {current:.1%} to {target:.1%}",
                "variants": ["control", "progressive_profiling", "interactive_tutorial"],
                "duration_days": 21,
                "ice": {"impact": 9, "confidence": 6, "ease": 6},
            },
            "retention_rate": {
                "name": f"{metric.replace('_', ' ').title()} Engagement Nudge Campaign",
                "hypothesis": f"Behavioral nudges will increase {metric} from {current:.1%} to {target:.1%}",
                "variants": ["control", "weekly_digest", "prediction_alerts"],
                "duration_days": 30,
                "ice": {"impact": 9, "confidence": 6, "ease": 7},
            },
            "referral_rate": {
                "name": f"{metric.replace('_', ' ').title()} Viral Loop Enhancement",
                "hypothesis": f"Improved referral incentives will increase {metric} from {current:.1%} to {target:.1%}",
                "variants": ["control", "credits_reward", "feature_unlock"],
                "duration_days": 21,
                "ice": {"impact": 7, "confidence": 6, "ease": 7},
            },
        }
        
        exp_template = experiments.get(metric, experiments["conversion_rate"])
        
        # Calculate ICE score
        ice = exp_template["ice"]
        ice_total = (ice["impact"] * 4) + (ice["confidence"] * 3) + (ice["ease"] * 3)
        
        return {
            "experiment_id": f"exp-{metric}-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "name": exp_template["name"],
            "hypothesis": exp_template["hypothesis"],
            "target_metric": metric,
            "current_value": current,
            "target_value": target,
            "expected_lift": f"{((target - current) / current * 100):.0f}%",
            "variants": exp_template["variants"],
            "duration_days": exp_template["duration_days"],
            "ice_scores": {
                "impact": ice["impact"],
                "confidence": ice["confidence"],
                "ease": ice["ease"],
                "total": ice_total,
            },
            "status": "proposed",
            "created_at": datetime.utcnow().isoformat(),
            "source": "metric_gap",
            "priority": gap["priority"],
        }

    async def _design_scout_experiment(
        self,
        opportunity: Dict[str, Any],
        metrics: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Design experiment from SCOUT opportunity.

        Args:
            opportunity: SCOUT opportunity
            metrics: Current metrics

        Returns:
            Experiment design
        """
        exp_type = opportunity.get("subtype", "landing_page_test")
        
        experiments = {
            "landing_page_test": {
                "name": "Real-Time Sentiment Display on Landing Page",
                "hypothesis": "Displaying real-time sentiment scores will increase conversion by leveraging FOMO",
                "target_metric": "conversion_rate",
                "variants": ["control", "sentiment_ticker", "fear_greed_meter"],
                "ice": {"impact": 8, "confidence": 7, "ease": 7},
                "duration_days": 14,
            },
        }
        
        template = experiments.get(exp_type, experiments["landing_page_test"])
        ice = template["ice"]
        ice_total = (ice["impact"] * 4) + (ice["confidence"] * 3) + (ice["ease"] * 3)
        
        return {
            "experiment_id": f"exp-scout-{datetime.utcnow().strftime('%Y%m%d-%H%M%S')}",
            "name": template["name"],
            "hypothesis": template["hypothesis"],
            "target_metric": template["target_metric"],
            "variants": template["variants"],
            "duration_days": template["duration_days"],
            "ice_scores": {
                "impact": ice["impact"],
                "confidence": ice["confidence"],
                "ease": ice["ease"],
                "total": ice_total,
            },
            "rationale": opportunity.get("rationale", ""),
            "status": "proposed",
            "created_at": datetime.utcnow().isoformat(),
            "source": "SCOUT",
            "priority": opportunity.get("priority", "Medium"),
        }

    def _prioritize_experiments(
        self, 
        experiments: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Prioritize experiments by ICE score and impact.

        Args:
            experiments: List of experiments

        Returns:
            Prioritized list
        """
        # Sort by ICE score descending
        sorted_exps = sorted(
            experiments,
            key=lambda x: (x["ice_scores"]["total"], x.get("priority") == "High"),
            reverse=True
        )
        
        # Remove duplicates (same target_metric)
        seen_metrics = set()
        unique = []
        for exp in sorted_exps:
            metric = exp["target_metric"]
            if metric not in seen_metrics:
                seen_metrics.add(metric)
                unique.append(exp)
        
        return unique[:5]  # Top 5 unique experiments

    async def _publish_experiment(self, experiment: Dict[str, Any]) -> None:
        """Publish experiment to Firestore and notify.

        Args:
            experiment: Experiment data
        """
        # Save to Firestore
        await self.firestore.save_experiment(
            experiment_id=experiment["experiment_id"],
            experiment_data=experiment,
        )

        # Publish event
        await self.pubsub.publish_experiment(experiment, agent_name="ELON")

        # Notify for high-priority
        if experiment["ice_scores"]["total"] >= self.high_ice_threshold:
            await self.telegram.notify_experiment_proposed(experiment, agent_name="ELON")

    async def _generate_growth_insights(
        self,
        metrics: Dict[str, Any],
        experiments: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Generate growth insights from analysis.

        Args:
            metrics: Current metrics
            experiments: Proposed experiments

        Returns:
            Growth insights
        """
        insights = []
        
        mrr = metrics.get("mrr", {})
        funnel = metrics.get("funnel", {})
        
        # Calculate potential MRR impact
        total_potential_lift = 0
        for exp in experiments:
            if exp["target_metric"] == "conversion_rate":
                # Estimate: 20% lift in conversion = 20% more MRR
                total_potential_lift += 0.20
            elif exp["target_metric"] == "retention_rate":
                # Retention has compound effect
                total_potential_lift += 0.30
        
        current_mrr = mrr.get("estimated_mrr", 1000)
        potential_mrr = current_mrr * (1 + total_potential_lift)
        
        insights.append({
            "type": "mrr_forecast",
            "current_mrr": current_mrr,
            "potential_mrr": potential_mrr,
            "potential_growth": f"+{total_potential_lift:.0%}",
            "confidence": "Medium",
            "note": "Based on proposed experiments if all succeed",
        })
        
        # Identify weakest funnel step
        conversion = funnel.get("conversion_rate", 0)
        activation = funnel.get("activation_rate", 0)
        retention = funnel.get("retention_rate", 0)
        
        weakest = min(
            ("conversion", conversion / self.target_metrics["conversion_rate"]),
            ("activation", activation / self.target_metrics["activation_rate"]),
            ("retention", retention / self.target_metrics["retention_rate"]),
            key=lambda x: x[1]
        )
        
        insights.append({
            "type": "bottleneck_identified",
            "weakest_step": weakest[0],
            "current_performance": f"{funnel.get(weakest[0] + '_rate', 0):.1%}",
            "target_performance": f"{self.target_metrics[weakest[0] + '_rate']:.1%}",
            "recommendation": f"Focus experiments on {weakest[0]} rate improvement",
        })
        
        return insights

    async def _generate_agent_requests(
        self,
        metrics: Dict[str, Any],
        experiments: List[Dict[str, Any]],
    ) -> Dict[str, List[Dict]]:
        """Generate requests for other agents.

        Args:
            metrics: Current metrics
            experiments: Proposed experiments

        Returns:
            Agent requests
        """
        requests = {
            "SETH": [],
            "ZARA": [],
        }
        
        # Request content from SETH based on gaps
        priority_gap = metrics.get("priority_gap")
        if priority_gap:
            requests["SETH"].append({
                "type": "content_request",
                "priority": priority_gap["priority"],
                "topic": f"How to Improve {priority_gap['metric'].replace('_', ' ').title()}",
                "rationale": f"Supporting experiment on {priority_gap['metric']}",
                "target_keyword": priority_gap["metric"].replace("_", " "),
            })
        
        # Request community support from ZARA
        requests["ZARA"].append({
            "type": "engagement_focus",
            "priority": "High",
            "focus": "support_experiments",
            "rationale": "Community feedback needed for upcoming experiments",
            "channels": ["reddit", "discord"],
        })
        
        return requests

    def _summarize_result(self, result: Dict[str, Any]) -> str:
        """Summarize results for notifications.

        Args:
            result: Execution results

        Returns:
            Summary string
        """
        experiments = result.get("experiments_proposed", [])
        high_ice = sum(1 for e in experiments if e.get("ice_scores", {}).get("total", 0) >= 32)
        
        metrics = result.get("metrics_snapshot", {})
        mrr = metrics.get("mrr", {})
        current_mrr = mrr.get("estimated_mrr", 0)
        growth = mrr.get("signup_growth_mom", 0)

        insights = result.get("growth_insights", [])
        forecast = next((i for i in insights if i["type"] == "mrr_forecast"), {})
        potential = forecast.get("potential_growth", "N/A")

        return (
            f"Proposed {len(experiments)} experiments "
            f"({high_ice} high ICE). "
            f"Current MRR: ${current_mrr:,.0f}, Growth: {growth:+.1%}. "
            f"Potential: {potential}"
        )

    async def get_experiment_backlog(
        self,
        status: Optional[str] = None,
        min_ice_score: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get experiment backlog.

        Args:
            status: Filter by status
            min_ice_score: Minimum ICE score

        Returns:
            List of experiments
        """
        experiments = await self.firestore.get_experiments(status=status, limit=100)
        
        filtered = [
            e for e in experiments
            if e.get("ice_scores", {}).get("total", 0) >= min_ice_score
        ]
        
        filtered.sort(
            key=lambda x: x.get("ice_scores", {}).get("total", 0),
            reverse=True
        )
        
        return filtered
