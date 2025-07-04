# 训练集： 145/306 = 47.3%
# 验证集： 9/25 = 36%
# 测试集：大概有 13 * 0.465 = 6
# BugFixed: 直接扔进模型，概率大的反而是负样本，不知道为啥。分特别低的原因
# 后处理，如果遇到台阶为True，则修改为Fasle

import sys

sys.path.insert(0, "../ML-tools")

from TabularTool.trainer import Trainer
from TabularTool.validator import CV
from lightgbm import LGBMClassifier, LGBMRegressor
import numpy as np
import pandas as pd
from sklearn.metrics import f1_score, fbeta_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import GroupKFold, KFold, StratifiedKFold


def build_data(base_dir):
    train = pd.read_csv(base_dir + "/t2_fea.csv")
    test = pd.read_csv(base_dir + "/t2_fea_test.csv")
    print("Data build finished", train.shape, test.shape)
    return train, test


def run_train(base_dir, seed=315):
    lgb_params = {
        "objective": "binary",
        "learning_rate": 0.01,
        "n_estimators": 64,
        "num_leaves": 2**3 - 1,
        "bagging_fraction": 0.85,
        # 'feature_fraction': 0.75,
        "seed": 2020,
    }

    fit_params = {
        "eval_metric": ["binary_error"],
        "verbose": 100,
        "early_stopping_rounds": 100,
    }

    x_train, x_test = build_data(base_dir)
    y_train = x_train["T2_CASE1"]
    feature_cols = [
        i
        for i in list(x_train.columns)
        if i
        not in [
            "SignalFileName",
            "T2_CASE1",
            "T2_CASE2",
            "T2_CASE3",
            "T2_CASE4",
            "abs_mean_mean_abs",
            "min_min2_main",
            "max_main_var",
        ]
    ]

    data_split = StratifiedKFold(n_splits=4, random_state=seed, shuffle=True)
    model = LGBMClassifier(**lgb_params)
    trainer = Trainer(model)

    trainer.train(
        x_train[feature_cols], y_train, categorical_feature=None, fit_params=fit_params
    )

    cv = CV(trainer, data_split)
    valid_oof, pred = cv.run(
        x_train,
        y_train,
        x_test=x_test,
        split_groups="T2_CASE1",
        feature_cols=feature_cols,
        categorical_feature=None,
        fit_params=fit_params,
        final_eval_metric=[
            get_precision_score,
            get_recall_score,
            get_f1_score,
            roc_auc_score,
        ],
        predict_method="predict_proba_positive",
    )
    cv.get_feature_importance(columns=feature_cols, save=True, save_dir="../../data")

    submit = pd.DataFrame()
    submit["SignalFileName"] = x_test["SignalFileName"]
    submit["score"] = pred
    submit.sort_values("score", ascending=False, ignore_index=True, inplace=True)
    submit["T2_CASE1"] = False
    submit.iloc[:6]["T2_CASE1"] = True
    submit.to_csv("../../data/result/t2c1_res.csv", index=False)
    print(np.mean(pred), len(pred))
    return


def get_f1_score(y_true, y_pred):
    y_pred = [1 if i > 0.5 else 0 for i in y_pred]
    return f1_score(y_true, y_pred)


def get_precision_score(y_true, y_pred):
    y_pred = [1 if i > 0.5 else 0 for i in y_pred]
    return precision_score(y_true, y_pred)


def get_recall_score(y_true, y_pred):
    y_pred = [1 if i > 0.5 else 0 for i in y_pred]
    return recall_score(y_true, y_pred)


if __name__ == "__main__":
    base_dir = "../../data/feature"
    run_train(base_dir)
