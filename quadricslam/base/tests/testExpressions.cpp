/* ----------------------------------------------------------------------------

 * QuadricSLAM Copyright 2020, ARC Centre of Excellence for Robotic Vision, Queensland University of Technology (QUT)
 * Brisbane, QLD 4000
 * All Rights Reserved
 * Authors: Lachlan Nicholson, et al. (see THANKS for the full author list)
 * See LICENSE for the license information

 * -------------------------------------------------------------------------- */

/**
 * @file testExpressions.cpp
 * @date Apr 14, 2020
 * @author Lachlan Nicholson
 * @brief an example of how to use gtsam expressions
 */

// The two new headers that allow using our Automatic Differentiation Expression framework
#include <gtsam/slam/expressions.h>
#include <gtsam/nonlinear/ExpressionFactorGraph.h>

// Header order is close to far
#include <gtsam/geometry/Point2.h>
#include <gtsam/nonlinear/DoglegOptimizer.h>
#include <gtsam/nonlinear/Values.h>
#include <gtsam/inference/Symbol.h>
#include <gtsam/base/Testable.h>

#include <vector>
#include <quadricslam/geometry/ConstrainedDualQuadric.h>

using namespace std;
using namespace gtsam;
using namespace noiseModel;

Vector3 f(Vector3 x, OptionalJacobian<3,3> H = boost::none) {
    if (H) {
        *H = (Matrix33() << 2*x(0), 0.0, 0.0,
                            0.0, 2*x(1), 0.0,
                            0.0, 0.0, 2*x(2)).finished();
    }
    return x.cwiseProduct(x);
}

Vector3 g(Vector3 y, OptionalJacobian<3,3> H) {
    if (H) {
        *H = (Matrix33() << 2*y(0), 0.0, 0.0,
                            0.0, 2*y(1), 0.0,
                            0.0, 0.0, 2*y(2)).finished();
    }
    return y.cwiseProduct(y);
}


Vector3 h(Vector3 y, OptionalJacobian<3,3> H) {
    return y.cwiseProduct(y);
}

namespace gtsam {
class Foo {
    private:
        Vector3 x_;
        Vector3 y_;

    public:
        Foo();
        Foo(Vector3 x, Vector3 y) : x_(x), y_(y) {};
        static Foo Create(Vector3 x, Vector3 y, OptionalJacobian<6,3> H1 = boost::none, OptionalJacobian<6,3> H2 = boost::none) {
            return Foo(x,y);
        }
        Vector3 doWork(const Vector3& z, OptionalJacobian<3,6> H1 = boost::none, OptionalJacobian<3,3> H2 = boost::none) const {
            return x_+y_+z;
        }

        // Foo retract(const Vector6& v) const {};
        // Vector6 localCoordinates(const Foo& other) const {};
        void print(const std::string& s = "") const {};
        bool equals(const Foo& other, double tol = 1e-9) const {};

};

template <>
struct traits<Foo> {
    enum { dimension = 6};
};

// template <>
// struct traits<Foo> : public Testable<Foo> {};

// template <>
// struct traits<const Foo> : public Testable<Foo> {};
}


ConstrainedDualQuadric constructQuadric(Pose3 pose, Vector3 radii, OptionalJacobian<9,6> H1, OptionalJacobian<9,3> H2) {
    return ConstrainedDualQuadric(pose, radii);
} 

Foo constructFoo(Vector3 x, Vector3 y, OptionalJacobian<6,3> H1, OptionalJacobian<6,3> H2) {
    return Foo(x,y);
}


void wrap_class(void) {
    // Expression<Pose3> p('p', 1);
    // Expression<Vector3> r('r', 1);
    // Expression<ConstrainedDualQuadric> Q1(&constructQuadric, p, r);
    // Expression<ConstrainedDualQuadric> Q2(&ConstrainedDualQuadric::Create, p, r);

    Expression<Vector3> x('x', 1);
    Expression<Vector3> y('y', 1);
    Expression<Vector3> z('z', 1);
    Values values;
    values.insert(symbol('x', 1), Vector3(1.,2.,3.));
    values.insert(symbol('y', 1), Vector3(2.,2.,2.));
    values.insert(symbol('z', 1), Vector3(3.,4.,5.));

    // Expression<Foo> foo1(&constructFoo, x, y); // need to provide dFoo_dx (6x3) and dFoo_dy (6x3)
    Expression<Foo> foo1(&Foo::Create, x, y);
    Expression<Vector3> result(foo1, &Foo::doWork, z); // need to provide dres_dFoo (3,6) and dres_dz (3,3)

    Vector3 res = result.value(values);
    cout << "res: " << res.transpose() << endl;
}

void without_expressions(void) {
    cout << "Test WITHOUT expressions: \n";
    
    // define x
    Vector3 x(1.,2.,3.);

    // calculate y and dy_dx
    Matrix33 dy_dx;
    Vector3 y = f(x, dy_dx);
    Vector3 t = f(x);

    // calculate g and dz_dy
    Matrix33 dz_dy;
    Vector3 z = g(y, dz_dy);

    // calculate dz_dx
    Matrix33 dz_dx = dz_dy * dy_dx;

    // print result and jacobian
    cout << "z: " << z.transpose() << endl;
    cout << "dz_dx:\n" << dz_dx << endl;
    
}

void with_expressions(void) {
    // define expression chain to calculate z from x
    // ensuring each function exposes jacobians along the way
    Expression<Vector3> x('x',1); // x = (1,2,3)
    Expression<Vector3> y(&f, x); // y = f(x)
    Expression<Vector3> z(&g, y); // z = g(y)

    // insert variables into values
    Values values;
    values.insert(symbol('x',1), Vector3(1.,2.,3.));

    // get result and jacobian
    std::vector<Matrix> gradients;
    Matrix3 dz_dx; gradients.push_back(dz_dx);
    Vector3 result = z.value(values, gradients);
    dz_dx = gradients[0];

    // print result and jacobian
    cout << "z: " << result.transpose() << endl;
    cout << "dz_dx:\n" << dz_dx << endl;
}

void print_expression(Expression<Vector3> e) {
    // print expression
    e.print("expression: ");

    // print keys
    std::set<Key> keys = e.keys();
    cout << "keys ";
    for (auto k : keys) {
        cout << symbolChr(k) << symbolIndex(k) << ' ';
    }
    cout << endl;

    // print dims
    std::map<Key, int> map;
    e.dims(map);
    cout << "dims " << endl;
    for (auto t : map) {
        cout << "map[" << symbolChr(t.first) << symbolIndex(t.first) << "] = " << t.second << endl;
    }
} 

void without_jacobians(void) {
    // define expression chain to calculate z from x
    // ensuring each function exposes jacobians along the way
    Expression<Vector3> x('x',1); // x = (1,2,3)
    Expression<Vector3> y(&h, x); // y = f(x)

    // insert variables into values
    Values values;
    values.insert(symbol('x',1), Vector3(1.,2.,3.));

    // get result and jacobian
    Vector3 result = y.value(values);

    // print result and jacobian
    cout << "z: " << result.transpose() << endl;
}


int main(void) {

    cout << "\nTEST: wrap_class\n";
    wrap_class();

    cout << "\nTEST: with_expressions\n";
    with_expressions();

    cout << "\nTEST: without_expressions\n";
    without_expressions();

    cout << "\nTEST: without_jacobians\n";
    without_jacobians();



    return 1;
}