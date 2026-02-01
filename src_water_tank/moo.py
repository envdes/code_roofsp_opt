from pymoo.core.problem import Problem
import numpy as np


# ref: https://pymoo.org/interface/problem.html
class MLProblem(Problem):
    def __init__(self, model=None, nvar=3, nobj=2, xl=[1.0, 35.0, 0.01], xu=[20.0, 65.0, 20.0]):
        super().__init__(n_var=nvar,  # 决策变量数量
                         n_obj=nobj,  # 目标函数数量
                         xl=xl,  # 决策变量下界
                         xu=xu # 决策变量上界
                         ) 
        
        if model:
            self.model = model
        else:
            raise ValueError("Model is required")

    def _evaluate(self, X, out, *args, **kwargs):
        # 机器学习模型的预测值
        predictions = self.model.predict(X)

        # 定义目标函数（示例：两个目标，一个是预测值，另一个是某种规则化项）
        f1 = predictions
        f2 = X[:,2]

        # 设置目标值
        out["F"] = np.column_stack([f1, f2])
        
        
        