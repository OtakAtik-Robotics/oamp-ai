import numpy as np
from sklearn.preprocessing import PolynomialFeatures
from sklearn.linear_model import LinearRegression

def estimate_cognitive_age(time_finish_one_task):
    degree = 2
    poly_features = PolynomialFeatures(degree=degree)

    x_time = np.array([9, 10, 11, 12, 14, 16, 18, 20, 25, 30, 35, 40, 45, 50]).reshape(-1, 1)
    y_age = np.array([20, 25, 30, 35, 40, 45, 50, 55, 60, 65, 70, 75, 80, 85])

    x_time_poly = poly_features.fit_transform(x_time)
    model_time = LinearRegression()
    model_time.fit(x_time_poly, y_age)

    new_x_time = np.array([time_finish_one_task]).reshape(-1, 1)
    new_x_time_poly = poly_features.transform(new_x_time)
    cognitive_age = model_time.predict(new_x_time_poly)

    if cognitive_age < 20:
        cognitive_age = 20
    elif cognitive_age > 85:
        cognitive_age = 90
        
    return int(cognitive_age)