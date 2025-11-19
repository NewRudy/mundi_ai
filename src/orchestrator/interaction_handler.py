"""
人机交互处理器
负责处理智能交互建议和自适应界面
"""

import json
import logging
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class UserInteraction:
    """用户交互记录"""
    interaction_id: str
    user_id: str
    interaction_type: str  # click, hover, input, voice, gesture
    target: str  # 交互目标
    timestamp: datetime
    context: Dict[str, Any] = field(default_factory=dict)
    duration: float = 0.0


@dataclass
class InteractionPattern:
    """交互模式"""
    pattern_id: str
    user_id: str
    pattern_type: str  # frequent, sequential, temporal
    actions: List[str]
    frequency: int = 0
    last_occurrence: datetime = None


@dataclass
class UIAdaptationRule:
    """UI自适应规则"""
    rule_id: str
    condition: str
    action: str
    priority: int = 1
    enabled: bool = True


class InteractionHandler:
    """人机交互处理器"""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

        # 交互历史
        self.interaction_history: List[UserInteraction] = []

        # 用户交互模式
        self.user_patterns: Dict[str, List[InteractionPattern]] = {}

        # UI自适应规则
        self.adaptation_rules: List[UIAdaptationRule] = []
        self._init_adaptation_rules()

        # 回调函数
        self.callbacks: Dict[str, List[Callable]] = {
            'interaction_recorded': [],
            'pattern_detected': [],
            'ui_adapted': [],
            'suggestion_generated': []
        }

    def _init_adaptation_rules(self):
        """初始化自适应规则"""
        rules = [
            UIAdaptationRule(
                rule_id="rule_001",
                condition="user_click_delay > 5_seconds",
                action="show_help_tooltip",
                priority=1
            ),
            UIAdaptationRule(
                rule_id="rule_002",
                condition="repeated_errors > 3",
                action="simplify_interface",
                priority=2
            ),
            UIAdaptationRule(
                rule_id="rule_003",
                condition="frequent_action_pattern",
                action="add_quick_access_button",
                priority=3
            ),
            UIAdaptationRule(
                rule_id="rule_004",
                condition="screen_resolution < 1920x1080",
                action="optimize_layout_for_small_screen",
                priority=1
            ),
            UIAdaptationRule(
                rule_id="rule_005",
                condition="expert_user_detected",
                action="show_advanced_options",
                priority=2
            )
        ]

        self.adaptation_rules.extend(rules)

    def record_interaction(self, user_id: str, interaction_type: str,
                         target: str, **context) -> str:
        """
        记录用户交互

        Args:
            user_id: 用户ID
            interaction_type: 交互类型
            target: 交互目标
            **context: 上下文信息

        Returns:
            交互记录ID
        """
        import uuid
        interaction_id = str(uuid.uuid4())

        interaction = UserInteraction(
            interaction_id=interaction_id,
            user_id=user_id,
            interaction_type=interaction_type,
            target=target,
            timestamp=datetime.now(),
            context=context
        )

        self.interaction_history.append(interaction)

        # 触发回调
        self._trigger_callback('interaction_recorded', interaction)

        # 分析交互模式
        self._analyze_interaction_patterns(user_id)

        return interaction_id

    def _analyze_interaction_patterns(self, user_id: str):
        """分析用户交互模式"""
        # 获取用户最近100条交互记录
        user_interactions = [
            i for i in self.interaction_history[-100:]
            if i.user_id == user_id
        ]

        if len(user_interactions) < 10:
            return  # 数据不足

        # 检测频繁操作模式
        frequent_actions = {}
        for interaction in user_interactions:
            action_key = f"{interaction.interaction_type}_{interaction.target}"
            frequent_actions[action_key] = frequent_actions.get(action_key, 0) + 1

        # 找出出现频率超过30%的操作
        threshold = len(user_interactions) * 0.3
        for action, count in frequent_actions.items():
            if count > threshold:
                self._record_pattern(
                    user_id=user_id,
                    pattern_type="frequent",
                    actions=[action],
                    frequency=count
                )

        # 检测时间模式
        self._detect_temporal_patterns(user_id, user_interactions)

    def _detect_temporal_patterns(self, user_id: str, interactions: List[UserInteraction]):
        """检测时间模式"""
        if not interactions:
            return

        # 检查是否在工作时间操作
        hourly_distribution = {}
        for interaction in interactions:
            hour = interaction.timestamp.hour
            hourly_distribution[hour] = hourly_distribution.get(hour, 0) + 1

        # 找出最常操作的时间段
        peak_hour = max(hourly_distribution.items(), key=lambda x: x[1])[0]

        self._record_pattern(
            user_id=user_id,
            pattern_type="temporal",
            actions=[f"peak_hour_{peak_hour}"],
            frequency=hourly_distribution[peak_hour]
        )

    def _record_pattern(self, user_id: str, pattern_type: str,
                       actions: List[str], frequency: int):
        """记录交互模式"""
        import uuid
        pattern_id = str(uuid.uuid4())

        pattern = InteractionPattern(
            pattern_id=pattern_id,
            user_id=user_id,
            pattern_type=pattern_type,
            actions=actions,
            frequency=frequency,
            last_occurrence=datetime.now()
        )

        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = []

        # 检查是否已存在相同模式
        existing_pattern = None
        for p in self.user_patterns[user_id]:
            if p.pattern_type == pattern_type and p.actions == actions:
                existing_pattern = p
                break

        if existing_pattern:
            existing_pattern.frequency += frequency
            existing_pattern.last_occurrence = datetime.now()
        else:
            self.user_patterns[user_id].append(pattern)

        # 触发回调
        self._trigger_callback('pattern_detected', pattern)

    def generate_suggestions(self, user_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成智能交互建议

        Args:
            user_id: 用户ID
            context: 上下文信息

        Returns:
            建议列表
        """
        suggestions = []

        # 分析用户交互模式
        patterns = self.user_patterns.get(user_id, [])

        for pattern in patterns:
            if pattern.pattern_type == "frequent":
                # 频繁操作建议
                suggestions.append({
                    "suggestion_id": f"freq_{pattern.pattern_id}",
                    "type": "shortcut",
                    "message": "检测到您经常执行此操作，是否需要添加到快速访问？",
                    "action": "add_to_quick_access",
                    "priority": 2,
                    "pattern": pattern
                })

        # 基于上下文的建议
        current_view = context.get("current_view", "")
        if current_view == "flood_simulation":
            suggestions.append({
                "suggestion_id": "flood_tip_001",
                "type": "tip",
                "message": "试试使用快捷键 Ctrl+F 快速加载洪水数据",
                "action": "show_tip",
                "priority": 1
            })
        elif current_view == "reservoir_operation":
            suggestions.append({
                "suggestion_id": "reservoir_tip_001",
                "type": "tip",
                "message": "优化调度方案可提升15%发电效率",
                "action": "suggest_optimization",
                "priority": 3
            })

        # 自适应学习优化
        learning_suggestions = self._generate_learning_suggestions(user_id, context)
        suggestions.extend(learning_suggestions)

        # 按优先级排序
        suggestions.sort(key=lambda s: s["priority"], reverse=True)

        # 触发回调
        self._trigger_callback('suggestion_generated', {
            "user_id": user_id,
            "suggestions": suggestions
        })

        return {
            "user_id": user_id,
            "suggestion_count": len(suggestions),
            "suggestions": suggestions
        }

    def _generate_learning_suggestions(self, user_id: str, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成学习优化建议"""
        suggestions = []

        # 分析交互历史长度（判断新手还是专家）
        user_interactions = [i for i in self.interaction_history if i.user_id == user_id]

        if len(user_interactions) < 20:
            # 新用户，提供新手引导
            suggestions.append({
                "suggestion_id": "onboarding_001",
                "type": "guide",
                "message": "欢迎使用水电智能运维系统！是否需要新手引导？",
                "action": "show_onboarding",
                "priority": 1
            })
        elif len(user_interactions) > 100:
            # 专家用户，提供高级功能
            suggestions.append({
                "suggestion_id": "expert_001",
                "type": "feature",
                "message": "您已熟练使用基础功能，试试高级分析工具？",
                "action": "show_advanced_tools",
                "priority": 2
            })

        return suggestions

    def adapt_interface(self, user_id: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        自适应界面调整

        Args:
            user_id: 用户ID
            current_state: 当前UI状态

        Returns:
            调整后的UI配置
        """
        adaptations = []

        # 评估每条规则
        for rule in self.adaptation_rules:
            if not rule.enabled:
                continue

            if self._evaluate_rule(rule, user_id, current_state):
                adaptations.append({
                    "rule_id": rule.rule_id,
                    "action": rule.action,
                    "priority": rule.priority
                })

        # 生成自适应UI配置
        ui_config = self._generate_ui_config(adaptations)

        # 触发回调
        self._trigger_callback('ui_adapted', {
            "user_id": user_id,
            "adaptations": adaptations,
            "ui_config": ui_config
        })

        return {
            "user_id": user_id,
            "adaptation_count": len(adaptations),
            "adaptations": adaptations,
            "ui_config": ui_config
        }

    def _evaluate_rule(self, rule: UIAdaptationRule, user_id: str,
                      current_state: Dict[str, Any]) -> bool:
        """评估自适应规则"""
        condition = rule.condition

        # 简化的规则评估逻辑
        if "user_click_delay" in condition:
            # 检查点击延迟
            delay = current_state.get("last_click_delay", 0)
            threshold = 5  # 5秒
            return delay > threshold

        elif "repeated_errors" in condition:
            # 检查重复错误
            error_count = current_state.get("recent_errors", 0)
            threshold = 3
            return error_count > threshold

        elif "frequent_action_pattern" in condition:
            # 检查频繁操作模式
            patterns = self.user_patterns.get(user_id, [])
            for pattern in patterns:
                if pattern.frequency > 10:  # 出现超过10次
                    return True
            return False

        elif "screen_resolution" in condition:
            # 检查屏幕分辨率
            resolution = current_state.get("screen_resolution", [1920, 1080])
            if isinstance(resolution, list) and len(resolution) >= 2:
                return resolution[0] < 1920
            return False

        elif "expert_user_detected" in condition:
            # 检测专家用户
            user_interactions = [i for i in self.interaction_history if i.user_id == user_id]
            return len(user_interactions) > 100

        return False

    def _generate_ui_config(self, adaptations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成UI配置"""
        config = {
            "layout": "default",
            "show_help": False,
            "show_quick_access": False,
            "show_advanced": False,
            "simplify_mode": False
        }

        # 按优先级排序
        adaptations.sort(key=lambda a: a["priority"])

        for adaptation in adaptations:
            action = adaptation["action"]

            if action == "show_help_tooltip":
                config["show_help"] = True
            elif action == "simplify_interface":
                config["simplify_mode"] = True
            elif action == "add_quick_access_button":
                config["show_quick_access"] = True
            elif action == "optimize_layout_for_small_screen":
                config["layout"] = "compact"
            elif action == "show_advanced_options":
                config["show_advanced"] = True

        return config

    def execute_scenario(self, scenario_type: str, **parameters) -> Dict[str, Any]:
        """
        执行业务场景

        Args:
            scenario_type: 场景类型
            **parameters: 参数

        Returns:
            场景执行结果
        """
        # 这里与业务场景层集成
        self.logger.info(f"执行业务场景: {scenario_type}")

        return {
            "status": "success",
            "scenario_type": scenario_type,
            "message": f"场景 {scenario_type} 开始执行"
        }

    def get_interaction_stats(self, user_id: str = None) -> Dict[str, Any]:
        """获取交互统计"""
        if user_id:
            interactions = [i for i in self.interaction_history if i.user_id == user_id]
        else:
            interactions = self.interaction_history

        if not interactions:
            return {"interaction_count": 0}

        # 统计交互类型
        type_stats = {}
        for interaction in interactions:
            type_stats[interaction.interaction_type] = type_stats.get(
                interaction.interaction_type, 0
            ) + 1

        return {
            "total_interactions": len(interactions),
            "interaction_types": type_stats,
            "unique_users": len(set(i.user_id for i in interactions)),
            "average_duration": sum(i.duration for i in interactions) / len(interactions)
        }

    def register_callback(self, event: str, callback: Callable):
        """注册回调"""
        if event in self.callbacks:
            self.callbacks[event].append(callback)

    def _trigger_callback(self, event: str, data: Any):
        """触发回调"""
        if event in self.callbacks:
            for callback in self.callbacks[event]:
                try:
                    callback(data)
                except Exception as e:
                    self.logger.error(f"回调执行失败: {e}")
