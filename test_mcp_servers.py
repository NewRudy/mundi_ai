#!/usr/bin/env python3
"""
MCP服务器测试脚本
验证所有专业模型MCP服务器的功能
"""

import asyncio
import numpy as np
from datetime import datetime, timedelta
from src.mcp_servers.integration import hydropower_mcp_server

async def test_flood_evolution_server():
    """测试洪水演进服务器"""
    print("=== 测试洪水演进模型MCP服务器 ===")

    try:
        from src.mcp_servers.flood_evolution_mcp import FloodEvolutionMCPServer
        server = FloodEvolutionMCPServer()

        result = await server.simulate_flood_propagation(
            river_length=50.0,
            simulation_hours=12.0,
            upstream_flow_rate=2000.0,
            downstream_water_level=8.0,
            manning_roughness=0.035,
            bed_slope=0.001,
            initial_water_level=4.0,
            bank_height=6.0
        )

        if result.get("status") == "success":
            print("✓ 洪水演进模拟成功")
            print(f"  - 最大水位: {result['results']['max_water_level']:.2f}m")
            print(f"  - 最大流量: {result['results']['max_discharge']:.2f}m³/s")
            print(f"  - 风险等级: {result['results']['max_risk_level']}")
            return True
        else:
            print(f"✗ 洪水演进模拟失败: {result.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 洪水演进服务器测试失败: {e}")
        return False

async def test_reservoir_simulation_server():
    """测试水库模拟服务器"""
    print("\n=== 测试水库模拟模型MCP服务器 ===")

    try:
        from src.mcp_servers.reservoir_simulation_mcp import ReservoirSimulationMCPServer
        server = ReservoirSimulationMCPServer()

        result = await server.simulate_reservoir_operation(
            current_water_level=165.0,
            forecast_hours=24,
            average_inflow=8000.0,
            operation_mode="normal",
            target_water_level=170.0
        )

        if result.get("status") == "success":
            print("✓ 水库调度模拟成功")
            print(f"  - 平均泄流: {result['statistics']['avg_outflow']:.2f}m³/s")
            print(f"  - 期末水位: {result['statistics']['final_water_level']:.2f}m")
            print(f"  - 发电量: {result['statistics']['total_power_generation_mwh']:.2f}MWh")
            return True
        else:
            print(f"✗ 水库调度模拟失败: {result.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 水库模拟服务器测试失败: {e}")
        return False

async def test_anomaly_detection_server():
    """测试异常检测服务器"""
    print("\n=== 测试异常检测模型MCP服务器 ===")

    try:
        from src.mcp_servers.anomaly_detection_mcp import AnomalyDetectionMCPServer
        server = AnomalyDetectionMCPServer()

        # 生成测试数据 (包含一些异常)
        normal_water_levels = np.random.normal(10.0, 0.5, 100)
        normal_discharges = np.random.normal(5000.0, 200.0, 100)

        # 添加一些异常点
        normal_water_levels[20] = 15.0  # 异常高水位
        normal_discharges[50] = 8000.0  # 异常大流量

        result = await server.detect_hydrological_anomalies(
            water_level_data=normal_water_levels.tolist(),
            discharge_data=normal_discharges.tolist(),
            seasonal_period=24,
            sensitivity="medium"
        )

        if result.get("status") == "success":
            print("✓ 异常检测成功")
            print(f"  - 异常检测率: {result['detection_summary']['anomaly_detection_rate']:.2%}")
            print(f"  - 水位异常数: {result['detection_summary']['water_level_anomalies']}")
            print(f"  - 流量异常数: {result['detection_summary']['discharge_anomalies']}")
            print(f"  - 严重程度: {result['severity_assessment']['overall_severity']}")
            return True
        else:
            print(f"✗ 异常检测失败: {result.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 异常检测服务器测试失败: {e}")
        return False

async def test_risk_assessment_server():
    """测试风险评估服务器"""
    print("\n=== 测试风险评估模型MCP服务器 ===")

    try:
        from src.mcp_servers.risk_assessment_mcp import RiskAssessmentMCPServer
        server = RiskAssessmentMCPServer()

        result = await server.assess_comprehensive_risk(
            current_water_level=12.5,
            current_discharge=6000.0,
            historical_max_level=15.0,
            historical_max_discharge=10000.0,
            dam_height=20.0,
            population_density=200.0,
            structure_age=25,
            design_standard=85.0,
            maintenance_score=80.0,
            inspection_score=90.0
        )

        if result.get("status") == "success":
            print("✓ 综合风险评估成功")
            overall_risk = result["risk_assessment"]["overall_risk"]["risk_level"]
            total_score = result["risk_assessment"]["overall_risk"]["total_score"]
            print(f"  - 总体风险等级: {overall_risk}")
            print(f"  - 综合风险评分: {total_score:.3f}")
            print(f"  - 级联风险: {result['risk_assessment']['overall_risk']['cascading_risk']:.3f}")
            return True
        else:
            print(f"✗ 综合风险评估失败: {result.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 风险评估服务器测试失败: {e}")
        return False

async def test_prediction_server():
    """测试预测模型服务器"""
    print("\n=== 测试预测模型MCP服务器 ===")

    try:
        from src.mcp_servers.prediction_mcp import PredictionMCPServer
        server = PredictionMCPServer()

        # 生成模拟的历史数据
        time_points = 168  # 一周的数据
        base_water_level = 10.0
        base_discharge = 5000.0

        # 添加季节性和趋势
        water_levels = []
        discharges = []

        for i in range(time_points):
            # 日周期
            daily_cycle = np.sin(2 * np.pi * i / 24) * 0.5
            # 周周期
            weekly_cycle = np.sin(2 * np.pi * i / (24 * 7)) * 0.3
            # 随机噪声
            noise = np.random.normal(0, 0.2)

            water_level = base_water_level + daily_cycle + weekly_cycle + noise
            discharge = base_discharge + daily_cycle * 200 + weekly_cycle * 100 + noise * 100

            water_levels.append(water_level)
            discharges.append(discharge)

        result = await server.predict_hydrological_variables(
            historical_water_levels=water_levels,
            historical_discharges=discharges,
            prediction_hours=24,
            method="ensemble",
            seasonal_period=24,
            confidence_level=0.95
        )

        if result.get("status") == "success":
            print("✓ 水文变量预测成功")
            water_level_pred = result["water_level_prediction"]["predicted_values"]
            discharge_pred = result["discharge_prediction"]["predicted_values"]
            accuracy = result["accuracy_assessment"]["quality_level"]
            print(f"  - 预测数据点: {len(water_level_pred)} 个")
            print(f"  - 水位预测范围: {min(water_level_pred):.2f} - {max(water_level_pred):.2f}m")
            print(f"  - 流量预测范围: {min(discharge_pred):.2f} - {max(discharge_pred):.2f}m³/s")
            print(f"  - 预测质量: {accuracy}")
            return True
        else:
            print(f"✗ 水文变量预测失败: {result.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 预测服务器测试失败: {e}")
        return False

async def test_integration_server():
    """测试集成服务器"""
    print("\n=== 测试MCP服务器集成 ===")

    try:
        # 生成测试数据
        test_water_levels = np.random.normal(10.0, 0.5, 100).tolist()
        test_discharges = np.random.normal(5000.0, 200.0, 100).tolist()

        result = await hydropower_mcp_server.run_integrated_analysis(
            water_level_data=test_water_levels,
            discharge_data=test_discharges
        )

        if result.get("status") == "success":
            print("✓ 综合分析成功")
            system_health = result["integrated_analysis"]["overall_assessment"]["system_health"]
            urgency_level = result["integrated_analysis"]["overall_assessment"]["urgency_level"]
            print(f"  - 系统健康状态: {system_health}")
            print(f"  - 紧急程度: {urgency_level}")
            print(f"  - 建议数量: {len(result['integrated_analysis']['overall_assessment']['recommendations'])} 条")
            return True
        else:
            print(f"✗ 综合分析失败: {result.get('message', '未知错误')}")
            return False

    except Exception as e:
        print(f"✗ 集成服务器测试失败: {e}")
        return False

async def test_system_status():
    """测试系统状态"""
    print("\n=== 测试系统状态 ===")

    try:
        status = await hydropower_mcp_server.get_system_status()

        if status.get("status") == "operational":
            print("✓ 系统状态正常")
            servers = status.get("servers", {})
            for server_name, server_info in servers.items():
                print(f"  - {server_name}: {server_info['status']}")
            return True
        else:
            print("✗ 系统状态异常")
            return False

    except Exception as e:
        print(f"✗ 系统状态测试失败: {e}")
        return False

async def run_all_tests():
    """运行所有测试"""
    print("开始MCP服务器功能测试...")
    print("=" * 50)

    tests = [
        ("洪水演进服务器", test_flood_evolution_server),
        ("水库模拟服务器", test_reservoir_simulation_server),
        ("异常检测服务器", test_anomaly_detection_server),
        ("风险评估服务器", test_risk_assessment_server),
        ("预测模型服务器", test_prediction_server),
        ("集成服务器", test_integration_server),
        ("系统状态", test_system_status)
    ]

    results = []

    for test_name, test_func in tests:
        try:
            success = await test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"✗ {test_name} 测试异常: {e}")
            results.append((test_name, False))

    # 汇总结果
    print("\n" + "=" * 50)
    print("测试结果汇总:")

    passed = 0
    for test_name, success in results:
        status = "✓ 通过" if success else "✗ 失败"
        print(f"{test_name}: {status}")
        if success:
            passed += 1

    print(f"\n总计: {passed}/{len(results)} 个测试通过")

    if passed == len(results):
        print("🎉 所有MCP服务器测试通过！系统运行正常。")
        return True
    else:
        print("⚠️ 部分测试失败，请检查相关服务器实现。")
        return False

if __name__ == "__main__":
    print("MCP服务器功能测试")
    print("=" * 50)

    try:
        success = asyncio.run(run_all_tests())
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n测试被用户中断")
        exit(1)
    except Exception as e:
        print(f"\n测试过程中发生错误: {e}")
        exit(1)